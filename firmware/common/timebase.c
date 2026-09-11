/*
 * timebase.c — Timer0 1ms 시각 + Idle 슬립 (구현)
 *
 * 요강 대응: TCCR0A / TCCR0B / OCR0A / TIMSK0 / SMCR 을 직접 제어한다.
 * avr-libc 의 sleep.h 매크로 대신 SMCR 비트를 직접 세우고 sleep 명령을
 * 인라인 어셈블리로 넣었다.
 */

#ifndef F_CPU
#define F_CPU 16000000UL
#endif

#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/atomic.h>

#include "timebase.h"

/*
 * 16MHz / 64 = 250kHz. 250 카운트마다 비교 일치 -> 정확히 1kHz.
 * OCR0A 는 0부터 세므로 250-1 = 249.
 * 16MHz 가 64 로도 250 으로도 나누어떨어지므로 오차가 없다.
 */
#define TIMEBASE_OCR  249

static volatile uint32_t g_ms;

ISR(TIMER0_COMPA_vect) {
  g_ms++;
}

void timebase_init(void) {
  g_ms = 0;

  /*
   * WGM02:0 = 010 : CTC 모드, TOP = OCR0A
   * COM0A/COM0B = 00 : 비교 출력을 핀으로 내보내지 않는다.
   *                    PD5(OC0B), PD6(OC0A) 를 다른 용도로 쓸 수 있게 유지.
   * CS02:0 = 011 : 프리스케일러 64
   */
  TCCR0A = (1 << WGM01);
  TCCR0B = (1 << CS01) | (1 << CS00);
  OCR0A  = TIMEBASE_OCR;
  TCNT0  = 0;

  /* 잔여 플래그를 지우고(1을 써야 지워진다) 비교 일치 인터럽트를 켠다. */
  TIFR0  = (1 << OCF0A);
  TIMSK0 = (1 << OCIE0A);
}

uint32_t timebase_ms(void) {
  uint32_t v;

  /* 32비트라 8비트 MCU 에서는 원자적이지 않다. 반드시 감싸서 읽는다. */
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    v = g_ms;
  }
  return v;
}

void timebase_sleep(void) {
  /*
   * SM2:0 = 000 : Idle 모드. CPU 코어와 Flash 만 멈추고 Timer0/Timer1,
   *               Analog Comparator, ADC, TWI, USART 는 계속 동작한다.
   * SE    = 1   : 슬립 허용. 깨어난 뒤 곧바로 내려 실수로 다시 자는 것을 막는다.
   */
  SMCR = (1 << SE);
  __asm__ __volatile__ ("sleep" ::: "memory");
  SMCR = 0;
}

void timebase_delay_ms(uint32_t ms) {
  uint32_t t0 = timebase_ms();

  while ((uint32_t)(timebase_ms() - t0) < ms) {
    timebase_sleep();
  }
}
