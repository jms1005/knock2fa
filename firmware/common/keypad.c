/*
 * keypad.c — 4키 디바운스와 짧게/길게 판정 (구현)
 */

#include <avr/io.h>

#include "keypad.h"

/*
 * PD2 ~ PD5 (Arduino Uno 의 D2~D5).
 * PD4 는 Timer0 외부 클럭 입력(T0), PD5 는 OC0B 와 핀을 공유하지만,
 * 이 프로젝트는 Timer0 를 내부 클럭 CTC 모드로만 쓰고 비교 출력을 핀으로
 * 내보내지 않으므로 (COM0B = 00) 충돌하지 않는다.
 */
#define KEY_DDR   DDRD
#define KEY_PORT  PORTD
#define KEY_PINR  PIND
#define KEY_BASE  PD2

/* 눌린 상태로 지난 폴링 횟수. 0이면 떼어져 있음 */
static uint16_t g_held[KEYPAD_KEYS];
/* 길게가 이미 발동했으면 뗄 때 짧게로 또 세지 않는다 */
static uint8_t  g_long_fired[KEYPAD_KEYS];

void keypad_init(void) {
  uint8_t i;
  uint8_t mask = 0;

  for (i = 0; i < KEYPAD_KEYS; i++) {
    mask |= (uint8_t)(1 << (KEY_BASE + i));
    g_held[i] = 0;
    g_long_fired[i] = 0;
  }
  KEY_DDR  &= (uint8_t)~mask;  /* 입력 */
  KEY_PORT |= mask;            /* 내부 풀업 */
}

uint8_t keypad_all_released(void) {
  uint8_t i;

  for (i = 0; i < KEYPAD_KEYS; i++) {
    /* 풀업이므로 눌리면 LOW */
    if (!(KEY_PINR & (1 << (KEY_BASE + i)))) {
      return 0;
    }
  }
  return 1;
}

keypad_result_t keypad_poll(void) {
  keypad_result_t r;
  uint8_t i;

  r.ev  = KEY_NONE;
  r.idx = 0;

  for (i = 0; i < KEYPAD_KEYS; i++) {
    uint8_t pressed = (uint8_t)((KEY_PINR & (1 << (KEY_BASE + i))) ? 0 : 1);

    if (pressed) {
      if (g_held[i] < 0xFFFF) {
        g_held[i]++;
      }
      if (!g_long_fired[i] && g_held[i] >= KEYPAD_LONG_TICKS) {
        g_long_fired[i] = 1;
        if (r.ev == KEY_NONE) {
          r.ev  = KEY_LONG;
          r.idx = i;
        }
      }
      continue;
    }

    /* 떼어진 순간 */
    if (g_held[i] > 0) {
      uint8_t was_long = g_long_fired[i];

      g_held[i] = 0;
      g_long_fired[i] = 0;
      /* 1틱(20ms) 미만은 채터링으로 간주해 버린다 */
      if (!was_long && r.ev == KEY_NONE) {
        r.ev  = KEY_SHORT;
        r.idx = i;
      }
    }
  }

  return r;
}
