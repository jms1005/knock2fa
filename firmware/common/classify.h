/*
 * classify.h — 방전 시간을 광학 지문으로 바꾸고 최근접 중심점으로 판정한다.
 *
 * 이 모듈은 의도적으로 <avr/io.h> 를 포함하지 않는다. PC에서 그대로
 * 컴파일해 단위 테스트할 수 있어야 하기 때문이다. 이 조건을 깨뜨리지 말 것.
 */

#ifndef CLASSIFY_H
#define CLASSIFY_H

#include <stdint.h>

#define CLASSIFY_CHANNELS     3
#define CLASSIFY_CLASSES      3

/* 컨덕턴스 스케일 상수. G = K / t 로 정수 유지 */
#define CLASSIFY_K            1000000000UL
/* 정규화 후 세 채널 합의 목표치 */
#define CLASSIFY_NORM_SUM     1000UL
/* 이 값보다 신호 합이 작으면 "빛이 사실상 없음"으로 본다 */
#define CLASSIFY_MIN_SIGNAL   3000UL
/* 곱셈 전 우측 시프트 기준. sum이 이 값 이하여야 i*1000 이 32비트에 들어간다 */
#define CLASSIFY_SHIFT_LIMIT  4000000UL

typedef enum {
  CLASSIFY_OK         = 0,
  CLASSIFY_LOW_SIGNAL = 1
} classify_status_t;

typedef struct {
  uint16_t          n[CLASSIFY_CHANNELS]; /* 정규화 지문. 합 ~ CLASSIFY_NORM_SUM */
  classify_status_t status;
} fingerprint_t;

typedef struct {
  int8_t   cls;  /* 0~2. 임계값 초과 또는 신호 부족이면 -1 (미상) */
  uint32_t d2;   /* 최소 제곱거리 */
  uint16_t dist; /* 표시용 정수 제곱근 */
} classify_result_t;

/*
 * 방전 시간(틱)을 정규화 지문으로 변환한다.
 * t == 0 은 PEDD_TIMEOUT 을 뜻하며 "빛이 오지 않았다"로 해석한다.
 * DARK 채널의 타임아웃은 정상이며 암전류 보정량이 0이 될 뿐이다.
 */
fingerprint_t classify_fingerprint(uint32_t t_dark, uint32_t t_r,
                                   uint32_t t_g, uint32_t t_b);

/* 지문을 중심점들과 비교해 가장 가까운 클래스를 고른다. */
classify_result_t classify_match(const fingerprint_t *fp,
                                 const uint16_t centroids[CLASSIFY_CLASSES][CLASSIFY_CHANNELS],
                                 uint32_t threshold_d2);

/* 정수 제곱근 (내림). 표시용. */
uint16_t classify_isqrt(uint32_t v);

#endif /* CLASSIFY_H */
