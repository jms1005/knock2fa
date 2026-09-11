/*
 * timebase.h — Timer0 기반 1ms 시각 + Idle 슬립
 *
 * 두 가지 이유로 둔다.
 *  1) 잠금 해제 실패 후의 대기 시간(패널티)을 세려면 절대 시간이 필요하다.
 *     _delay_ms() 로는 "전원을 껐다 켜면 초기화되는" 시간밖에 만들 수 없다.
 *  2) 대기 구간에서 CPU 를 Idle 슬립에 넣기 위한 기상 신호로 쓴다.
 *     잠금장치는 대부분의 시간을 아무 일 없이 보내므로, 그 동안 CPU 코어와
 *     Flash 를 멈추는 것이 실사용에 맞는 설계다.
 *
 * Idle 모드를 고른 이유
 *   Power-down 모드가 전류는 훨씬 적지만, 그 모드에서는 Analog Comparator 와
 *   Timer1 이 정지하므로 노크를 감지할 수 없다. 노크를 항상 받아야 하는 이
 *   시스템에서는 Idle 이 상한이다. 더 낮추려면 평상시엔 Power-down 으로 자고
 *   버튼(핀 체인지 인터럽트)으로 깨운 뒤 노크를 받는 2단 구조가 필요하며,
 *   이는 향후 과제로 남긴다.
 */

#ifndef TIMEBASE_H
#define TIMEBASE_H

#include <stdint.h>

/* Timer0 를 1ms 주기 CTC 로 기동한다. sei() 전에 호출해도 된다. */
void timebase_init(void);

/* 부팅 후 경과 밀리초. 32비트라 약 49.7일에 한 번 되돌아간다. */
uint32_t timebase_ms(void);

/*
 * CPU 를 Idle 슬립에 넣는다. 다음 인터럽트(최소한 1ms 틱)에서 깨어난다.
 * 조건 검사와 슬립 진입 사이의 경합을 걱정할 필요가 없다. Timer0 가 계속
 * 도는 한 최대 1ms 안에 반드시 깨어나므로 교착이 생기지 않는다.
 */
void timebase_sleep(void);

/* ms 밀리초 동안 슬립하며 대기한다. */
void timebase_delay_ms(uint32_t ms);

#endif /* TIMEBASE_H */
