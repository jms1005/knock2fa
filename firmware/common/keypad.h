/*
 * keypad.h — 택트 스위치 4개. 폴링 + 디바운스.
 *
 * 기존 PEDD 프로젝트의 button.c 를 4개 키로 확장한 것이다. 판정 규칙
 * (짧게 = 뗀 순간, 길게 = 2초를 채우는 순간)은 그대로 유지했다.
 *
 * 인터럽트를 쓰지 않는다. 노크 간격 측정이 Timer1 입력 캡처에 의존하는데,
 * 키 인터럽트가 끼어들면 캡처 ISR 진입이 늦어질 수 있기 때문이다.
 * (ICR1 래치 자체는 하드웨어라 값은 흔들리지 않지만, 잔향 에지가 연달아
 *  들어올 때 ISR 이 첫 에지를 읽기 전에 덮어쓰일 여지를 줄인다.)
 *
 * 스위치는 핀과 GND 사이에 연결하고 내부 풀업을 쓴다. 외부 저항이 없다.
 */

#ifndef KEYPAD_H
#define KEYPAD_H

#include <stdint.h>

#define KEYPAD_KEYS       4
#define KEYPAD_POLL_MS    20
#define KEYPAD_LONG_MS    2000
#define KEYPAD_LONG_TICKS (KEYPAD_LONG_MS / KEYPAD_POLL_MS)  /* 100 */

typedef enum {
  KEY_NONE  = 0,
  KEY_SHORT = 1,
  KEY_LONG  = 2
} keypad_event_t;

typedef struct {
  keypad_event_t ev;
  uint8_t        idx;   /* 0 ~ KEYPAD_KEYS-1. ev == KEY_NONE 이면 의미 없음 */
} keypad_result_t;

void keypad_init(void);

/*
 * KEYPAD_POLL_MS 주기로 호출한다.
 * 한 번의 호출은 이벤트를 하나만 돌려준다. 같은 20ms 창 안에서 두 키가
 * 동시에 처리되면 번호가 작은 쪽만 반환되고 나머지는 버려진다. 순서 입력은
 * 한 번에 한 키를 누르는 조작이므로 실사용에서 문제가 되지 않으며, 오히려
 * 두 키를 함께 눌러 순서를 흐리려는 입력을 자연스럽게 배제한다.
 */
keypad_result_t keypad_poll(void);

/* 모든 키가 떼어져 있으면 1. 모드 전환 후 잔여 입력을 흘려보낼 때 쓴다. */
uint8_t keypad_all_released(void);

#endif /* KEYPAD_H */
