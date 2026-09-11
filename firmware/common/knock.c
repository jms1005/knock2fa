/*
 * knock.c — 피에조 노크 검출 코어 (구현)
 *
 * 요강 대응: ACSR / ADCSRB / TCCR1B / TIMSK1 / ADMUX / ADCSRA 레지스터를
 *           직접 제어한다. 라이브러리 함수를 쓰지 않는다.
 */

#ifndef F_CPU
#define F_CPU 16000000UL
#endif

#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/atomic.h>

#include "knock.h"

/* ---- 핀 배정 ---- */
#define PIEZO_AC_DDR   DDRD
#define PIEZO_AC_PORT  PORTD
#define PIEZO_AC_BIT   PD7   /* AIN1. Analog Comparator 음극 입력이라 변경 불가 */
/* 진폭 측정용 ADC 채널. 같은 피에조 노드를 PC0 에도 연결한다. */
#define PIEZO_ADC_CH   0     /* ADC0 = PC0 */

/* ---- 시간 상수 (1틱 = 500ns) ---- */

/*
 * 링잉 불응기(blanking).
 * 압전 디스크와 부착면은 한 번의 타격에 대해 수 ms 동안 공진하므로,
 * 첫 검출 이후 일정 시간 동안의 추가 에지는 같은 노크의 잔향으로 보고
 * 버려야 한다. 이 값을 두지 않으면 노크 1회가 이벤트 3~5회로 잡혀
 * 간격 벡터가 통째로 무너진다.
 * 50ms 는 초당 20회까지 허용하므로 사람이 두드리는 속도에는 충분하다.
 * 실험 (1)에서 실제 파형을 보고 최종 확정할 것.
 */
#define BLANK_TICKS   (50UL   * KNOCKFP_TICKS_PER_MS)

/* 첫 노크를 기다리는 시간. 넘으면 사용자가 그만둔 것으로 본다. */
#define FIRST_TIMEOUT (6000UL  * KNOCKFP_TICKS_PER_MS)
/* 노크 사이 최대 대기 시간. */
#define GAP_TIMEOUT   (2000UL  * KNOCKFP_TICKS_PER_MS)
/* 진폭 포락선을 훑는 창. */
#define AMP_WINDOW    (2UL     * KNOCKFP_TICKS_PER_MS)

/*
 * 진폭 게이트.
 * 비교기 문턱(1.1V)은 하드웨어로 고정되어 있지만, 그 위에서 "얼마나 세게
 * 쳤는가"를 ADC 로 재서 소프트웨어로 한 번 더 거른다. 덕분에 문턱 조절용
 * 가변저항이나 DAC 회로 없이도 감도를 코드로 바꿀 수 있고, 지나가는 발소리
 * 같은 약한 진동을 배제할 수 있다.
 * AVCC=5V 기준 8비트이므로 1.1V ~ 56 LSB. 기본값 70(~1.37V)은 비교기 문턱을
 * 갓 넘긴 신호를 걸러내는 최소 여유다. 실험 (1)에서 조정할 것.
 */
#define AMP_MIN       70

/* ---- ISR 과 공유하는 상태 ---- */
static volatile uint16_t g_ovf;       /* Timer1 오버플로우 누적 */
static volatile uint32_t g_pend_ts;   /* 확정 대기 중인 노크 시각 */
static volatile uint8_t  g_pend;      /* 위 값이 유효한가 */
static volatile uint32_t g_last_ts;   /* 마지막으로 받아들인 에지 시각 (불응기 기준) */

/*
 * Timer1 Input Capture 인터럽트.
 * ISR 에서는 시각 기록과 불응기 판정만 한다. 나눗셈이나 화면 출력은 하지 않는다.
 */
ISR(TIMER1_CAPT_vect) {
  uint16_t icr = ICR1;
  uint16_t ovf = g_ovf;
  uint32_t now;

  /*
   * 오버플로우 경계 보정 (pedd.c 와 동일한 근거).
   * 캡처 인터럽트(벡터 10)가 오버플로우 인터럽트(벡터 13)보다 우선순위가
   * 높으므로, 오버플로우가 먼저 일어났는데 그 ISR 이 아직 실행되지 않은
   * 상태에서 여기로 진입할 수 있다. 그 경우 TOV1 이 아직 서 있고 ICR1 은
   * 매우 작다. 보정하지 않으면 32.768ms 단위의 이상값이 간헐적으로 섞인다.
   */
  if ((TIFR1 & (1 << TOV1)) && (icr < 0x8000)) {
    ovf++;
  }
  now = ((uint32_t)ovf << 16) | icr;

  /* 불응기 안이면 같은 노크의 잔향이므로 버린다. */
  if ((uint32_t)(now - g_last_ts) < BLANK_TICKS) {
    return;
  }
  g_last_ts = now;

  /* 앞의 노크가 아직 진폭 검사 중이면 이번 에지는 버린다(불응기 덕에 드물다). */
  if (g_pend) {
    return;
  }
  g_pend_ts = now;
  g_pend    = 1;
}

/* Timer1 오버플로우 — 16비트 카운터의 측정 범위를 32비트로 확장한다. */
ISR(TIMER1_OVF_vect) {
  g_ovf++;
}

/*
 * 현재 시각을 32비트로 읽는다.
 * TCNT1 을 먼저 읽고 g_ovf 를 읽는다. 그 사이에 오버플로우가 났다면 TCNT1 은
 * 0xFFFF 근처(큰 값)이므로 보정 조건에 걸리지 않고, 이미 오버플로우가 지난
 * 뒤라면 TCNT1 이 작은 값이므로 보정된다.
 */
static uint32_t timer_now(void) {
  uint16_t ovf, cnt;

  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    cnt = TCNT1;
    ovf = g_ovf;
    if ((TIFR1 & (1 << TOV1)) && (cnt < 0x8000)) {
      ovf++;
    }
  }
  return ((uint32_t)ovf << 16) | cnt;
}

/* ADC 단발 변환. ADLAR=1 이므로 상위 8비트만 읽는다. */
static uint8_t adc_sample(void) {
  ADCSRA |= (1 << ADSC);
  while (ADCSRA & (1 << ADSC)) {
    ;
  }
  return ADCH;
}

/* 노크 직후 AMP_WINDOW 동안의 최대 진폭을 찾는다. */
static uint8_t amp_peak(void) {
  uint32_t start = timer_now();
  uint8_t  peak  = 0;

  do {
    uint8_t v = adc_sample();
    if (v > peak) {
      peak = v;
    }
  } while ((uint32_t)(timer_now() - start) < AMP_WINDOW);

  return peak;
}

void knock_init(void) {
  /* 피에조 입력: 하이 임피던스. 내부 풀업을 켜면 DC 바이어스가 생겨 못 쓴다. */
  PIEZO_AC_DDR  &= (uint8_t)~(1 << PIEZO_AC_BIT);
  PIEZO_AC_PORT &= (uint8_t)~(1 << PIEZO_AC_BIT);

  /*
   * DIDR1 의 AIN1D=1 — PD7 의 디지털 입력 버퍼를 차단한다.
   * 아날로그 전압이 논리 문턱 근처에 머무를 때 버퍼가 발진하듯 소비 전류를
   * 끌어올리는 것을 막고, 노이즈도 줄인다.
   */
  DIDR1 |= (1 << AIN1D);
  /* 같은 이유로 ADC0(PC0) 의 디지털 버퍼도 차단한다. */
  DIDR0 |= (1 << ADC0D);

  /*
   * ADCSRB 의 ACME=0 — AIN1(PD7)을 비교기 음극 입력으로 고정한다.
   * ACME=1 로 ADC 멀티플렉서를 비교기 입력으로 끌어오는 방식은 ADEN=0,
   * 즉 ADC 를 꺼야만 동작한다. 이 프로젝트는 비교기(시각)와 ADC(진폭)를
   * 동시에 써야 하므로 그 방식을 쓸 수 없다. 대신 피에조 노드를 PD7 과
   * PC0 두 핀에 함께 연결해 두 주변장치가 독립적으로 같은 신호를 본다.
   */
  ADCSRB &= (uint8_t)~(1 << ACME);

  /*
   * ACSR 설정
   *   ACD  = 0 : 비교기 활성
   *   ACBG = 1 : 내부 1.1V 밴드갭을 양극 입력으로 선택.
   *              전원 전압과 온도에 따라 흔들리는 논리 문턱값 대신 쓴다.
   *   ACIC = 1 : 비교기 출력을 Timer1 Input Capture 에 연결.
   *              이 비트가 0이면 캡처가 아예 발생하지 않는다.
   *   ACIE = 0 : 비교기 자체 인터럽트는 쓰지 않는다 (캡처 인터럽트만 사용)
   */
  ACSR = (1 << ACBG) | (1 << ACIC);

  /*
   * ADC 설정
   *   REFS0 = 1     : 기준 전압 AVCC(5V)
   *   ADLAR = 1     : 결과를 좌측 정렬해 ADCH 한 바이트만 읽는다.
   *                   8비트로 낮추는 대신 16비트 원자적 읽기 부담이 사라진다.
   *   MUX   = ADC0
   *   ADPS  = /16   : 16MHz / 16 = 1MHz. 데이터시트가 10비트 정확도를 보장하는
   *                   50~200kHz 범위를 넘지만, 여기서 필요한 것은 절대 정확도가
   *                   아니라 "얼마나 셌나"의 상대 비교다. 변환 1회가 13us 로
   *                   줄어 2ms 창에서 약 150 표본을 얻을 수 있고, 그래야 수 kHz
   *                   로 공진하는 피에조 포락선의 최대치를 놓치지 않는다.
   */
  ADMUX  = (1 << REFS0) | (1 << ADLAR) | (PIEZO_ADC_CH & 0x0F);
  ADCSRA = (1 << ADEN) | (1 << ADPS2);

  /* 첫 변환은 25 ADC 클럭이 걸리고 값도 부정확하므로 버린다. */
  (void)adc_sample();

  /*
   * Timer1
   *   ICNC1 = 1 : 입력 캡처 노이즈 캔슬러. 4개 표본이 연속으로 같을 때만
   *               에지로 인정한다. 문턱 근처에서 비교기 출력이 채터링하는
   *               것을 하드웨어에서 걸러준다. ACIC=1 일 때 비교기 출력도
   *               이 캔슬러를 거친다. 4클럭(250ns)의 고정 지연이 생기지만
   *               모든 노크에 동일하게 적용되므로 간격에는 영향이 없다.
   *   ICES1 = 0 : 하강 에지 캡처.
   *               평상시 V(PD7) ~ 0V < 1.1V 이므로 ACO = 1 이고,
   *               노크로 1.1V 를 넘으면 ACO 가 1 -> 0 이 된다.
   *               (pedd.c 는 방전 방향이 반대라 상승 에지를 썼다. 혼동 주의)
   *   CS11  = 1 : 프리스케일러 /8 -> 2MHz -> 500ns 분해능,
   *               오버플로우 주기 32.768ms
   */
  TCCR1A = 0;
  TCCR1B = (1 << ICNC1) | (1 << CS11);

  TIMSK1 = (1 << ICIE1) | (1 << TOIE1);

  /*
   * 밴드갭 기준 전압 안정화 대기. 매 측정마다 켜고 끄지 않고 계속 유지한다.
   *
   * 여기서는 32비트 timer_now() 를 쓰지 않는다. knock_init() 은 main() 에서
   * sei() 보다 먼저 불리므로 오버플로우 ISR 이 아직 돌지 않고, 32비트 시각이
   * 전진하지 않을 수 있기 때문이다. 대기 시간 10ms = 20,000틱은 오버플로우
   * 주기(65,536틱)보다 짧으므로 16비트 모듈러 뺄셈만으로 정확히 셀 수 있다.
   * TCNT1 은 16비트라 읽기가 원자적이지 않지만, 이 시점에는 인터럽트가
   * 꺼져 있어 TEMP 레지스터가 침범당하지 않는다.
   */
  {
    uint16_t t0 = TCNT1;
    while ((uint16_t)(TCNT1 - t0) < (uint16_t)(10UL * KNOCKFP_TICKS_PER_MS)) {
      ;
    }
  }
}

knock_result_t knock_capture(void (*on_knock)(uint8_t idx)) {
  knock_result_t r;
  uint32_t ts[KNOCKFP_TAPS];
  uint32_t deadline_span;
  uint32_t ref;
  uint8_t  n = 0;
  uint8_t  k;

  for (k = 0; k < CLASSIFY_CHANNELS; k++) {
    r.gap[k] = 0;
  }
  for (k = 0; k < KNOCKFP_TAPS; k++) {
    r.amp[k] = 0;
    ts[k]    = 0;
  }

  /*
   * 대기 중 쌓인 잔여 이벤트를 버리고 시작한다.
   * 불응기 기준을 "지금"이 아니라 "한 불응기 전"으로 잡는다. 그냥 지금으로
   * 두면 캡처를 시작한 직후 50ms 동안 첫 노크가 통째로 무시되어, 화면이
   * 바뀌자마자 두드린 사용자의 첫 타를 놓친다. (부호 없는 뺄셈이므로
   * 시작 시각이 BLANK_TICKS 보다 작아도 모듈러 연산으로 올바르게 동작한다)
   */
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    g_pend    = 0;
    g_last_ts = timer_now() - BLANK_TICKS;
  }

  ref           = timer_now();
  deadline_span = FIRST_TIMEOUT;

  while (n < KNOCKFP_TAPS) {
    uint8_t  got = 0;
    uint32_t now_ts = 0;

    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
      if (g_pend) {
        now_ts = g_pend_ts;
        got    = 1;
      }
    }

    if (got) {
      uint8_t peak = amp_peak();

      /* 진폭이 모자라면 노크로 인정하지 않는다 (환경 진동 배제). */
      if (peak >= AMP_MIN) {
        ts[n]    = now_ts;
        r.amp[n] = peak;
        n++;
        if (on_knock != 0) {
          on_knock((uint8_t)(n - 1));
        }
        ref           = timer_now();
        deadline_span = GAP_TIMEOUT;
      }

      /* 진폭 검사가 끝났으므로 다음 에지를 받을 수 있게 연다. */
      ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        g_pend = 0;
      }
      continue;
    }

    if ((uint32_t)(timer_now() - ref) >= deadline_span) {
      r.status = (n == 0) ? KNOCK_TIMEOUT_FIRST : KNOCK_TIMEOUT_GAP;
      r.count  = n;
      return r;
    }
  }

  for (k = 0; k < CLASSIFY_CHANNELS; k++) {
    r.gap[k] = ts[k + 1] - ts[k];
  }
  r.status = KNOCK_OK;
  r.count  = n;
  return r;
}
