/*
 * knock2fa — 버튼 시퀀스 + 노크 리듬 이중 인증(2FA) 잠금 시스템
 *
 * 인증 구조
 *   1단계 (지식, Knowledge) : 등록된 버튼 4개를 정해진 순서로 누른다.
 *   2단계 (행동, Inherence) : 표면을 두드리는 리듬을 압전 소자로 측정해
 *                             등록된 사용자의 패턴과 비교한다.
 *   두 단계는 서로 다른 물리 채널(디지털 GPIO / 아날로그 비교기+ADC)에서
 *   독립적으로 얻어지며, 두 결과가 같은 사용자를 가리켜야만 해제된다.
 *   순서만 알아내도, 리듬만 흉내내도 뚫리지 않는다.
 *
 * 배선 (Arduino Uno 보드 기준)
 *   D2~D5 (PD2~PD5)  택트 스위치 4개 - GND 사이. 외부 저항 없음
 *   D7    (PD7,AIN1) 피에조 (+) 노드 -> 비교기 음극 입력  : 노크 시각
 *   A0    (PC0,ADC0) 같은 피에조 노드 -> ADC 입력         : 노크 진폭
 *   A4/A5 (PC4/PC5)  OLED SDA / SCL
 *   D9    (PB1)      잠금 액추에이터 (데모용 LED 또는 서보 신호)
 *   D1    (PD1)      UART TX 38400 8N1
 *   피에조 노드에 1MΩ 블리드 저항(GND), 1kΩ 직렬 보호 저항.
 *
 * 화면 문구는 전부 PSTR() 로 감싸 Flash 에 둔다. AVR 은 일반 문자열
 * 리터럴을 부팅 시 SRAM 으로 복사하는데, 문구가 많아 2KB 를 금방 잠식한다.
 */

#ifndef F_CPU
#define F_CPU 16000000UL
#endif

#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/pgmspace.h>

#include "classify.h"
#include "knockfp.h"
#include "knock.h"
#include "keypad.h"
#include "timebase.h"
#include "authstore.h"
#include "ssd1306.h"
#include "uart.h"

/* ---- 액추에이터 ---- */
#define LOCK_DDR   DDRB
#define LOCK_PORT  PORTB
#define LOCK_BIT   PB1

#define UNLOCK_MS       3000UL   /* 해제 유지 시간 */
#define PIN_IDLE_MS     10000UL  /* 순서 입력 도중 아무 입력이 없으면 취소 */
#define MSG_MS          2500UL   /* 결과 화면 유지 시간 */
#define ENROLL_REPEAT   5        /* 등록 시 리듬 반복 입력 횟수 */
/*
 * 등록 중 리듬이 연속으로 이만큼 실패하면 등록을 포기한다.
 * 이 한도가 없으면, 사용자가 계속 규칙에 맞지 않는 리듬(너무 빠르거나 너무
 * 긴)을 입력할 때 등록 화면에서 영원히 빠져나오지 못한다.
 */
#define ENROLL_MAX_BAD  5

/*
 * 등록 시 자동 임계값 = (표본들이 중심점에서 벗어난 최대 제곱거리) x 여유배수.
 * 임계값을 손으로 정하지 않고 사용자 본인의 재현성에서 유도한다. 리듬이
 * 일정한 사람은 좁게, 들쭉날쭉한 사람은 넓게 잡히므로 오거부를 줄이면서도
 * 필요 이상으로 헐거워지지 않는다.
 */
#define THRESHOLD_MARGIN  2

typedef enum {
  ST_LOCKOUT = 0,
  ST_IDLE,
  ST_PIN,
  ST_GRANTED,
  ST_DENIED,
  ST_ENROLL_PIN,
  ST_ENROLL_KNOCK,
  ST_ENROLL_DONE,
  ST_ENROLL_FAIL
} state_t;

static auth_db_t g_db;
static uint8_t   g_pin_buf[AUTH_PIN_LEN];
static uint8_t   g_pin_len;
static uint32_t  g_seq;          /* UART 로그의 시도 번호 */

/* 등록 진행 상태 */
static uint8_t       g_enroll_slot;
static uint8_t       g_enroll_done;
static uint8_t       g_enroll_bad;
static fingerprint_t g_enroll_fp[ENROLL_REPEAT];

/* ---- 보조 출력 ---- */

/* uart.c 를 고치지 않고 Flash 문자열을 보내기 위한 보조 함수 */
static void uart_puts_p(const char *s) {
  char c;

  while ((c = (char)pgm_read_byte(s)) != 0) {
    uart_putc(c);
    s++;
  }
}

/* 부호 없는 10진수를 문자열로. buf 는 최소 11바이트. */
static void u32_to_str(uint32_t v, char *buf) {
  char tmp[11];
  uint8_t i = 0;
  uint8_t j = 0;

  if (v == 0) {
    buf[0] = '0';
    buf[1] = 0;
    return;
  }
  while (v > 0) {
    tmp[i++] = (char)('0' + (v % 10));
    v /= 10;
  }
  while (i > 0) {
    buf[j++] = tmp[--i];
  }
  buf[j] = 0;
}

/* '*' 를 n개 채운 문자열을 만든다. buf 는 최소 AUTH_PIN_LEN+1 바이트. */
static void stars(char *buf, uint8_t n) {
  uint8_t i;

  for (i = 0; i < n && i < AUTH_PIN_LEN; i++) {
    buf[i] = '*';
  }
  buf[i] = 0;
}

static void lock_close(void) {
  LOCK_PORT &= (uint8_t)~(1 << LOCK_BIT);
}

static void lock_open(void) {
  LOCK_PORT |= (uint8_t)(1 << LOCK_BIT);
}

/* ---- 화면 ---- */

static void screen_idle(void) {
  ssd1306_clear();
  ssd1306_puts_p(0, 0, PSTR("KNOCK 2FA LOCK"));
  ssd1306_puts_p(1, 0, PSTR("---------------------"));
  if (g_db.users == 0) {
    ssd1306_puts_p(3, 0, PSTR("NOT ENROLLED"));
    ssd1306_puts_p(5, 0, PSTR("HOLD KEY1 2s"));
    ssd1306_puts_p(6, 0, PSTR("TO ENROLL"));
  } else {
    ssd1306_puts_p(3, 0, PSTR("STEP 1 / KNOWLEDGE"));
    ssd1306_puts_p(5, 0, PSTR("ENTER KEY SEQUENCE"));
  }
}

static void screen_seq_header(const char *title_p) {
  ssd1306_clear();
  ssd1306_puts_p(0, 0, title_p);
  ssd1306_puts_p(1, 0, PSTR("---------------------"));
  ssd1306_puts_p(3, 0, PSTR("PRESS 4 KEYS"));
}

/* 입력한 자릿수만큼 '*' 를 찍는다. 어떤 키인지는 보여주지 않는다. */
static void screen_pin_progress(void) {
  char buf[AUTH_PIN_LEN + 1];

  ssd1306_puts_p(6, 0, PSTR("      "));
  stars(buf, g_pin_len);
  ssd1306_puts(6, 0, buf);
}

static void screen_knock_prompt(uint8_t remain_repeat) {
  char buf[12];

  ssd1306_clear();
  ssd1306_puts_p(0, 0, PSTR("STEP 2 / RHYTHM"));
  ssd1306_puts_p(1, 0, PSTR("---------------------"));
  ssd1306_puts_p(3, 0, PSTR("KNOCK 4 TIMES"));
  if (remain_repeat > 0) {
    ssd1306_puts_p(5, 0, PSTR("REPEAT LEFT:"));
    u32_to_str(remain_repeat, buf);
    ssd1306_puts(5, 13, buf);
  }
}

/* 노크가 하나 잡힐 때마다 진행 표시를 갱신한다. */
static void on_knock_progress(uint8_t idx) {
  ssd1306_puts_p(7, (uint8_t)(idx * 2), PSTR("*"));
}

static void screen_result(uint8_t granted, int8_t user) {
  char buf[12];

  ssd1306_clear();
  if (granted) {
    ssd1306_puts_p(0, 0, PSTR("*** UNLOCKED ***"));
    ssd1306_puts_p(1, 0, PSTR("---------------------"));
    ssd1306_puts_p(3, 0, PSTR("USER"));
    u32_to_str((uint32_t)((uint8_t)user + 1), buf);
    ssd1306_puts(3, 5, buf);
    ssd1306_puts_p(6, 0, PSTR("HOLD KEY1: RE-ENROLL"));
  } else {
    ssd1306_puts_p(0, 0, PSTR("### DENIED ###"));
    ssd1306_puts_p(1, 0, PSTR("---------------------"));
    ssd1306_puts_p(3, 0, PSTR("TRIES LEFT:"));
    u32_to_str((uint32_t)(AUTH_FAIL_MAX - authstore_fail_get()), buf);
    ssd1306_puts(3, 12, buf);
  }
}

static void screen_lockout(uint32_t remain_ms) {
  char buf[12];

  ssd1306_clear();
  ssd1306_puts_p(0, 0, PSTR("!!! LOCKED OUT !!!"));
  ssd1306_puts_p(1, 0, PSTR("---------------------"));
  ssd1306_puts_p(3, 0, PSTR("TOO MANY FAILURES"));
  ssd1306_puts_p(5, 0, PSTR("WAIT"));
  u32_to_str((remain_ms + 999UL) / 1000UL, buf);
  ssd1306_puts(5, 5, buf);
  ssd1306_puts_p(5, 12, PSTR("SEC"));
}

/* ---- UART 로그 ---- */

static void log_header(void) {
  uart_puts_p(PSTR("# knock2fa log"));
  uart_newline();
  uart_puts_p(PSTR("seq,mode,pin_user,knock_user,d2,thr,n0,n1,n2,"
                   "g0ms,g1ms,g2ms,a0,a1,a2,a3,result"));
  uart_newline();
}

static void log_csv(const char *mode_p, int8_t pin_user, int8_t knock_user,
                    uint32_t d2, uint32_t thr, const fingerprint_t *fp,
                    const knock_result_t *kr, const char *result_p) {
  uint8_t k;

  uart_put_u32(g_seq);
  uart_putc(',');
  uart_puts_p(mode_p);
  uart_putc(',');
  /* 미상은 -1 대신 빈 칸으로 둔다. 분석 스크립트에서 결측으로 읽힌다. */
  if (pin_user >= 0) {
    uart_put_u32((uint32_t)pin_user);
  }
  uart_putc(',');
  if (knock_user >= 0) {
    uart_put_u32((uint32_t)knock_user);
  }
  uart_putc(',');
  uart_put_u32(d2);
  uart_putc(',');
  uart_put_u32(thr);

  for (k = 0; k < CLASSIFY_CHANNELS; k++) {
    uart_putc(',');
    uart_put_u32(fp->n[k]);
  }
  for (k = 0; k < CLASSIFY_CHANNELS; k++) {
    uart_putc(',');
    uart_put_u32(knock_ticks_to_ms(kr->gap[k]));
  }
  for (k = 0; k < KNOCKFP_TAPS; k++) {
    uart_putc(',');
    uart_put_u32(kr->amp[k]);
  }
  uart_putc(',');
  uart_puts_p(result_p);
  uart_newline();
}

/* ---- 인증 ---- */

/*
 * 입력된 순서와 일치하는 사용자를 찾는다. 없으면 -1.
 * 조기 반환하지 않고 항상 전 슬롯 · 전 자릿수를 비교한다. 일치하는 자릿수에
 * 따라 응답 시간이 달라지면 그 차이로 순서를 한 자리씩 알아낼 수 있다.
 */
static int8_t pin_lookup(const uint8_t *entered) {
  int8_t  found = -1;
  uint8_t u, k;

  for (u = 0; u < AUTH_USERS; u++) {
    uint8_t diff = 0;

    for (k = 0; k < AUTH_PIN_LEN; k++) {
      diff |= (uint8_t)(g_db.pin[u][k] ^ entered[k]);
    }
    if (diff == 0 && u < g_db.users) {
      found = (int8_t)u;
    }
  }
  return found;
}

/*
 * 노크 한 세트를 받아 지문으로 만든다.
 * 실패하면 fp->status 가 CLASSIFY_OK 가 아니게 되어 이후 판정이 자동 거부된다.
 */
static uint8_t take_rhythm(knock_result_t *kr, fingerprint_t *fp) {
  uint8_t k;

  *kr = knock_capture(on_knock_progress);
  if (kr->status != KNOCK_OK) {
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      fp->n[k] = 0;
    }
    fp->status = CLASSIFY_LOW_SIGNAL;
    return 0;
  }
  return (uint8_t)(knockfp_make(kr->gap, fp) == KNOCKFP_OK);
}

/*
 * 2단계 인증 본체. 순서 입력이 끝난 뒤에 호출된다.
 * 성공하면 1을 반환하고 *user 에 사용자 번호를 넣는다.
 */
static uint8_t run_auth(int8_t *user) {
  knock_result_t    kr;
  fingerprint_t     fp;
  classify_result_t cr;
  int8_t   pin_user;
  uint8_t  granted = 0;
  uint32_t thr;

  /*
   * [보안] 평가하기 전에 실패 카운터를 먼저 올린다.
   * 평가 후에 올리면, 결과가 확정되기 직전에 전원을 끊어 카운터를 회피하고
   * 무제한으로 시도할 수 있다. 성공했을 때만 나중에 0으로 되돌린다.
   */
  authstore_fail_set((uint8_t)(authstore_fail_get() + 1));

  pin_user = pin_lookup(g_pin_buf);
  /*
   * 임계값은 사용자별로 저장되어 있다(authstore.h 참고). classify_match() 는
   * 스칼라 임계값 하나만 받으므로, 여기서 지식 인증으로 알아낸 pin_user 의
   * 몫을 골라 넘긴다. cls 가 pin_user 와 다르면 어차피 아래에서 거부되므로
   * "엉뚱한 사용자의 임계값으로 통과 여부가 갈리는" 경우는 생기지 않는다.
   * pin_user 를 못 찾았을 때는 어떤 값을 넘겨도 granted 는 0이므로 0으로 둔다.
   */
  thr = (pin_user >= 0) ? g_db.threshold_d2[pin_user] : 0;

  screen_knock_prompt(0);
  if (take_rhythm(&kr, &fp)) {
    cr = classify_match(&fp,
                        (const uint16_t (*)[CLASSIFY_CHANNELS])g_db.centroid,
                        thr);
    /*
     * 두 인증 계층이 같은 사용자를 가리켜야 한다.
     * 순서만 맞고 리듬이 다른 사람이면 cr.cls != pin_user 가 되어 거부된다.
     * cr.cls 는 임계값을 넘으면 -1 이므로, pin_user >= 0 조건과 합쳐지면
     * "둘 다 성립하고 둘이 같다"만 통과한다.
     */
    if (pin_user >= 0 && cr.cls == pin_user) {
      granted = 1;
      *user   = pin_user;
    }
    log_csv(PSTR("AUTH"), pin_user, cr.cls, cr.d2, thr, &fp, &kr,
            granted ? PSTR("GRANT") : PSTR("DENY"));
  } else {
    log_csv(PSTR("AUTH"), pin_user, -1, 0, thr, &fp, &kr,
            PSTR("BADKNOCK"));
  }

  if (granted) {
    authstore_fail_set(0);
  }
  g_seq++;
  return granted;
}

/* ---- 등록 ---- */

/* 등록을 시작할 슬롯을 고른다. 빈 슬롯이 없으면 0번을 덮어쓴다. */
static uint8_t enroll_slot_pick(void) {
  if (g_db.users < AUTH_USERS) {
    return g_db.users;
  }
  return 0;
}

/*
 * 반복 입력이 끝난 뒤 중심점과 임계값을 확정해 저장한다.
 * 표본이 너무 흩어져 있으면 저장하지 않고 0을 반환한다.
 */
static uint8_t enroll_commit(void) {
  uint16_t centroid[CLASSIFY_CHANNELS];
  uint32_t spread;
  uint32_t th;
  uint8_t  k;

  knockfp_centroid(g_enroll_fp, ENROLL_REPEAT, centroid);
  spread = knockfp_spread_d2(g_enroll_fp, ENROLL_REPEAT, centroid);
  th = spread * THRESHOLD_MARGIN;

  /*
   * 흩어짐이 너무 크면 그 사용자의 리듬은 재현성이 없다는 뜻이다.
   * 임계값을 무리하게 넓혀 저장하면 타인도 통과하게 되므로 등록을 거부한다.
   */
  if (th > AUTH_THRESHOLD_MAX) {
    return 0;
  }
  if (th < AUTH_THRESHOLD_MIN) {
    th = AUTH_THRESHOLD_MIN;
  }

  for (k = 0; k < AUTH_PIN_LEN; k++) {
    g_db.pin[g_enroll_slot][k] = g_pin_buf[k];
  }
  for (k = 0; k < CLASSIFY_CHANNELS; k++) {
    g_db.centroid[g_enroll_slot][k] = centroid[k];
  }
  if (g_enroll_slot >= g_db.users) {
    g_db.users = (uint8_t)(g_enroll_slot + 1);
  }
  /* 이 사용자 슬롯만의 임계값. 다른 이미 등록된 사용자에게는 영향 없다. */
  g_db.threshold_d2[g_enroll_slot] = th;

  authstore_save(&g_db);
  /* 등록 직후에는 실패 이력을 초기화한다. */
  authstore_fail_set(0);
  return 1;
}

/* ---- 메인 ---- */

int main(void) {
  state_t  state;
  uint32_t state_t0;
  uint32_t last_input;
  uint32_t last_poll;

  LOCK_DDR |= (uint8_t)(1 << LOCK_BIT);
  lock_close();

  uart_init();
  timebase_init();
  keypad_init();
  knock_init();
  ssd1306_init();   /* 실패해도 계속 진행한다. UART 로깅은 살아 있어야 한다. */
  sei();

  log_header();

  (void)authstore_load(&g_db);

  g_pin_len     = 0;
  g_seq         = 0;
  g_enroll_slot = 0;
  g_enroll_done = 0;
  g_enroll_bad  = 0;
  state_t0      = timebase_ms();
  last_input    = state_t0;
  last_poll     = state_t0;

  if (authstore_fail_get() >= AUTH_FAIL_MAX) {
    /*
     * 부팅 시점에 이미 실패 한도를 넘겨 있다면, 전원을 껐다 켜서 잠금을
     * 회피하려는 시도일 수 있다. 대기 시간을 처음부터 다시 채우게 한다.
     */
    state = ST_LOCKOUT;
    screen_lockout(AUTH_LOCKOUT_MS);
  } else {
    state = ST_IDLE;
    screen_idle();
  }

  for (;;) {
    keypad_result_t kev;
    uint32_t now = timebase_ms();

    /* 20ms 주기 폴링. 그 사이에는 Idle 슬립으로 CPU 를 멈춘다. */
    if ((uint32_t)(now - last_poll) < KEYPAD_POLL_MS) {
      timebase_sleep();
      continue;
    }
    last_poll = now;
    kev = keypad_poll();

    switch (state) {

      case ST_LOCKOUT: {
        uint32_t elapsed = (uint32_t)(now - state_t0);

        if (elapsed >= AUTH_LOCKOUT_MS) {
          /* 벌칙을 다 채웠으므로 카운터를 되돌리고 정상 상태로 돌아간다. */
          authstore_fail_set(0);
          state    = ST_IDLE;
          state_t0 = now;
          screen_idle();
        } else if ((elapsed % 1000UL) < KEYPAD_POLL_MS) {
          screen_lockout(AUTH_LOCKOUT_MS - elapsed);
        }
        break;
      }

      case ST_IDLE:
        if (kev.ev == KEY_LONG && kev.idx == 0 && g_db.users == 0) {
          /* 최초 등록. 등록된 사용자가 있으면 인증 없이는 등록할 수 없다. */
          g_enroll_slot = enroll_slot_pick();
          g_pin_len     = 0;
          state         = ST_ENROLL_PIN;
          state_t0      = now;
          last_input    = now;
          screen_seq_header(PSTR("ENROLL 1/2 : SEQ"));
        } else if (kev.ev == KEY_SHORT && g_db.users > 0) {
          g_pin_buf[0] = kev.idx;
          g_pin_len    = 1;
          state        = ST_PIN;
          state_t0     = now;
          last_input   = now;
          screen_seq_header(PSTR("STEP 1 / KEY SEQ"));
          screen_pin_progress();
        }
        break;

      case ST_PIN:
        if (kev.ev == KEY_SHORT) {
          g_pin_buf[g_pin_len] = kev.idx;
          g_pin_len++;
          last_input = now;
          screen_pin_progress();

          if (g_pin_len >= AUTH_PIN_LEN) {
            int8_t user = -1;

            if (run_auth(&user)) {
              lock_open();
              screen_result(1, user);
              state = ST_GRANTED;
            } else {
              screen_result(0, -1);
              state = ST_DENIED;
            }
            g_pin_len = 0;
            /* 노크 입력에 수 초가 걸렸으므로 시각 기준을 다시 잡는다. */
            state_t0  = timebase_ms();
            last_poll = state_t0;
          }
        } else if ((uint32_t)(now - last_input) >= PIN_IDLE_MS) {
          /* 입력하다 만 상태로 방치되면 취소한다. */
          g_pin_len = 0;
          state     = ST_IDLE;
          state_t0  = now;
          screen_idle();
        }
        break;

      case ST_GRANTED:
        if (kev.ev == KEY_LONG && kev.idx == 0) {
          /*
           * [보안] 재등록은 인증에 성공한 직후에만 허용한다.
           * 대기 화면에서 아무나 길게 눌러 등록을 덮어쓸 수 있으면
           * 잠금장치의 의미가 없다.
           */
          lock_close();
          g_enroll_slot = enroll_slot_pick();
          g_pin_len     = 0;
          state         = ST_ENROLL_PIN;
          state_t0      = now;
          last_input    = now;
          screen_seq_header(PSTR("ENROLL 1/2 : SEQ"));
        } else if ((uint32_t)(now - state_t0) >= UNLOCK_MS) {
          lock_close();
          state    = ST_IDLE;
          state_t0 = now;
          screen_idle();
        }
        break;

      case ST_DENIED:
        if ((uint32_t)(now - state_t0) >= MSG_MS) {
          if (authstore_fail_get() >= AUTH_FAIL_MAX) {
            state    = ST_LOCKOUT;
            state_t0 = now;
            screen_lockout(AUTH_LOCKOUT_MS);
          } else {
            state    = ST_IDLE;
            state_t0 = now;
            screen_idle();
          }
        }
        break;

      case ST_ENROLL_PIN:
        if (kev.ev == KEY_SHORT) {
          g_pin_buf[g_pin_len] = kev.idx;
          g_pin_len++;
          last_input = now;
          screen_pin_progress();

          if (g_pin_len >= AUTH_PIN_LEN) {
            g_enroll_done = 0;
            g_enroll_bad  = 0;
            state         = ST_ENROLL_KNOCK;
            state_t0      = now;
          }
        } else if ((uint32_t)(now - last_input) >= PIN_IDLE_MS) {
          g_pin_len = 0;
          state     = ST_IDLE;
          state_t0  = now;
          screen_idle();
        }
        break;

      case ST_ENROLL_KNOCK: {
        knock_result_t kr;
        fingerprint_t  fp;

        screen_knock_prompt((uint8_t)(ENROLL_REPEAT - g_enroll_done));
        if (take_rhythm(&kr, &fp)) {
          g_enroll_fp[g_enroll_done] = fp;
          g_enroll_done++;
          g_enroll_bad = 0;
          log_csv(PSTR("ENROLL"), (int8_t)g_enroll_slot, -1, 0, 0, &fp, &kr,
                  PSTR("SAMPLE"));
          g_seq++;
        } else {
          log_csv(PSTR("ENROLL"), (int8_t)g_enroll_slot, -1, 0, 0, &fp, &kr,
                  PSTR("BADKNOCK"));
          g_seq++;
          g_enroll_bad++;
          if (kr.status == KNOCK_TIMEOUT_FIRST ||
              g_enroll_bad >= ENROLL_MAX_BAD) {
            /* 사용자가 그만두었거나 계속 실패하는 상황. 등록을 취소한다. */
            state     = ST_IDLE;
            state_t0  = timebase_ms();
            last_poll = state_t0;
            screen_idle();
            break;
          }
        }

        if (g_enroll_done >= ENROLL_REPEAT) {
          state    = enroll_commit() ? ST_ENROLL_DONE : ST_ENROLL_FAIL;
          state_t0 = timebase_ms();
          ssd1306_clear();
          if (state == ST_ENROLL_DONE) {
            ssd1306_puts_p(0, 0, PSTR("ENROLLED"));
            ssd1306_puts_p(1, 0, PSTR("---------------------"));
            ssd1306_puts_p(3, 0, PSTR("SAVED TO EEPROM"));
          } else {
            ssd1306_puts_p(0, 0, PSTR("ENROLL FAILED"));
            ssd1306_puts_p(1, 0, PSTR("---------------------"));
            ssd1306_puts_p(3, 0, PSTR("RHYTHM TOO"));
            ssd1306_puts_p(4, 0, PSTR("INCONSISTENT"));
            ssd1306_puts_p(6, 0, PSTR("TRY A SIMPLER ONE"));
          }
          last_poll = state_t0;
        }
        break;
      }

      case ST_ENROLL_DONE:
      case ST_ENROLL_FAIL:
        if ((uint32_t)(now - state_t0) >= MSG_MS) {
          g_pin_len = 0;
          state     = ST_IDLE;
          state_t0  = now;
          screen_idle();
        }
        break;

      default:
        state    = ST_IDLE;
        state_t0 = now;
        screen_idle();
        break;
    }
  }
}
