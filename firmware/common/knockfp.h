/*
 * knockfp.h — 노크 간격 벡터를 템포 정규화 지문으로 변환한다.
 *
 * 이 모듈은 classify.c 와 마찬가지로 <avr/io.h> 를 포함하지 않는다.
 * PC 에서 그대로 컴파일해 단위 테스트할 수 있어야 하기 때문이다.
 * 이 조건을 깨뜨리지 말 것.
 *
 * 왜 정규화가 필요한가 (설계 근거)
 *   간격을 절대 시간 그대로 비교하면, 같은 리듬을 조금 빠르게 두드리는
 *   것만으로 모든 성분이 함께 줄어들어 거리가 급격히 커진다. 즉 본인조차
 *   통과하지 못하는 오거부(FRR)가 발생한다.
 *   간격을 총 연주 길이로 나눈 "비율 벡터"를 쓰면 템포에 무관한 리듬의
 *   형태만 남으므로, 사람이 재현 가능한 수준의 변동을 흡수할 수 있다.
 *
 *     원본  [200ms, 400ms, 200ms]  ->  [250, 500, 250]
 *     1.5배 [300ms, 600ms, 300ms]  ->  [250, 500, 250]   (동일)
 *
 *   출력은 classify.h 의 fingerprint_t 를 그대로 쓴다. 따라서 판정은
 *   기존 classify_match() 를 한 줄도 고치지 않고 재사용한다.
 */

#ifndef KNOCKFP_H
#define KNOCKFP_H

#include <stdint.h>
#include "classify.h"

/* 노크 횟수. 간격 개수 = KNOCKFP_TAPS - 1 = CLASSIFY_CHANNELS 와 일치해야 한다. */
#define KNOCKFP_TAPS      (CLASSIFY_CHANNELS + 1)   /* 4회 두드림 -> 간격 3개 */

/*
 * 시간 단위는 knock.c 의 틱(1틱 = 500ns, Timer1 프리스케일러 /8 @16MHz).
 * 아래 상수도 전부 틱 단위다.  1ms = 2000틱.
 */
#define KNOCKFP_TICKS_PER_MS   2000UL

/* 간격 하한 40ms. 이보다 짧으면 링잉 잔여나 오검출로 본다. */
#define KNOCKFP_MIN_GAP    (40UL  * KNOCKFP_TICKS_PER_MS)
/* 총 연주 길이 허용 범위 150ms ~ 5000ms */
#define KNOCKFP_MIN_TOTAL  (150UL * KNOCKFP_TICKS_PER_MS)
#define KNOCKFP_MAX_TOTAL  (5000UL * KNOCKFP_TICKS_PER_MS)

/*
 * 곱셈 전 우측 시프트 기준.
 * total <= 이 값이어야 gap*CLASSIFY_NORM_SUM 이 uint32 에 들어간다.
 * (gap <= total 이므로 total*1000 = 4.0e9 < 4.294e9)
 * classify.c 의 CLASSIFY_SHIFT_LIMIT 와 같은 논리다.
 */
#define KNOCKFP_SHIFT_LIMIT  4000000UL

typedef enum {
  KNOCKFP_OK        = 0,
  KNOCKFP_TOO_FAST  = 1,  /* 간격 하나가 너무 짧다 (링잉 의심) */
  KNOCKFP_TOO_SHORT = 2,  /* 전체가 너무 짧다 */
  KNOCKFP_TOO_LONG  = 3   /* 전체가 너무 길다 */
} knockfp_status_t;

/*
 * 간격 벡터(틱)를 템포 정규화 지문으로 바꾼다.
 * 성공 시 fp->n[] 의 합은 CLASSIFY_NORM_SUM(=1000) 근처가 되고
 * fp->status 는 CLASSIFY_OK 가 된다.
 * 실패 시 fp->n[] 는 전부 0, fp->status 는 CLASSIFY_LOW_SIGNAL 이 되어
 * classify_match() 가 자동으로 판정을 거부한다.
 */
knockfp_status_t knockfp_make(const uint32_t gaps[CLASSIFY_CHANNELS],
                              fingerprint_t *fp);

/*
 * 등록용. 여러 번 반복 입력한 지문들의 평균(중심점)을 낸다.
 * n_samples 는 1 이상이어야 한다.
 */
void knockfp_centroid(const fingerprint_t *samples, uint8_t n_samples,
                      uint16_t out[CLASSIFY_CHANNELS]);

/*
 * 등록용. 표본들이 중심점에서 얼마나 흩어져 있는지(최대 제곱거리)를 구한다.
 * 이 값에 여유 배수를 곱해 인증 임계값으로 삼으면, 임계값을 손으로
 * 정하지 않고 사용자의 실제 재현성에서 유도할 수 있다.
 */
uint32_t knockfp_spread_d2(const fingerprint_t *samples, uint8_t n_samples,
                           const uint16_t centroid[CLASSIFY_CHANNELS]);

#endif /* KNOCKFP_H */
