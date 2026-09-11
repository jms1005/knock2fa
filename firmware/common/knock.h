/*
 * knock.h — 피에조 노크 검출 코어 (인터페이스)
 *
 * 측정 원리
 *   압전 디스크는 기계적 충격을 받으면 순간적으로 전압을 만든다. 이 전압을
 *   PD7(AIN1)에 넣고, Analog Comparator 의 양극 입력을 내부 1.1V 밴드갭으로
 *   고정해 비교한다. 평상시 V(PD7) ~ 0V 이므로 ACO = 1 이고, 노크로 1.1V 를
 *   넘어서는 순간 ACO 가 1 -> 0 으로 떨어진다. 이 하강 에지가 Timer1 의
 *   Input Capture 를 하드웨어로 트리거해 ICR1 에 시각이 기록된다.
 *
 * 왜 ADC 폴링이 아니라 하드웨어 캡처인가
 *   ADC 로 폴링하면 검출 시각이 샘플링 주기(수십 us)만큼 양자화되고,
 *   인터럽트 지연이 그대로 측정값에 섞인다. 리듬 인증은 간격의 재현성이
 *   전부이므로 이 지터를 없애야 한다. 입력 캡처는 ICR1 래치가 하드웨어에서
 *   일어나므로, ISR 이 늦게 실행되어도 기록된 시각은 흔들리지 않는다.
 *   기존 PEDD 프로젝트(pedd.c)에서 검증한 구조를 그대로 계승한다.
 *
 * 배선
 *   피에조(+) --+-- 1MΩ --GND        (블리드 저항: 전하 누적 방지, DC 0V 바이어스)
 *               +-- 1kΩ --+-- PD7 (AIN1)   비교기 음극 입력 = 시각 측정
 *                         +-- PC0 (ADC0)   ADC 입력       = 진폭 측정
 *   피에조(-) --------------- GND
 *   보호: 1kΩ 직렬 저항이 MCU 내부 클램프 다이오드로 흐르는 전류를 제한한다.
 *         더 확실히 하려면 PD7 노드에 1N4148 2개를 GND/VCC 로 클램프한다.
 */

#ifndef KNOCK_H
#define KNOCK_H

#include <stdint.h>
#include "knockfp.h"

typedef enum {
  KNOCK_OK            = 0,
  KNOCK_TIMEOUT_FIRST = 1,  /* 첫 노크가 오지 않음 (사용자 취소로 간주) */
  KNOCK_TIMEOUT_GAP   = 2   /* 중간에 끊김 */
} knock_status_t;

typedef struct {
  knock_status_t status;
  uint8_t  count;                       /* 실제로 받은 노크 수 */
  uint32_t gap[CLASSIFY_CHANNELS];      /* 노크 간격 (1틱 = 500ns) */
  uint8_t  amp[KNOCKFP_TAPS];           /* 각 노크의 진폭 (ADCH, 0~255) */
} knock_result_t;

/* Analog Comparator, Timer1, ADC, GPIO 초기화. 전원 투입 후 1회만 호출. */
void knock_init(void);

/*
 * KNOCKFP_TAPS 회의 노크를 받아 간격 벡터를 만든다.
 * on_knock 은 노크가 하나 확정될 때마다 호출된다(화면 갱신용). NULL 가능.
 * 인자는 0부터 시작하는 노크 순번.
 */
knock_result_t knock_capture(void (*on_knock)(uint8_t idx));

/* 틱 -> 밀리초 (표시용). 1틱 = 500ns 이므로 2000으로 나눈다. */
static inline uint32_t knock_ticks_to_ms(uint32_t ticks) {
  return ticks / KNOCKFP_TICKS_PER_MS;
}

#endif /* KNOCK_H */
