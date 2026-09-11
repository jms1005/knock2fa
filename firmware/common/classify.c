/*
 * classify.c — 광학 지문 계산과 최근접 중심점 판정
 *
 * 설계 근거는 docs/superpowers/specs/2026-09-03-phase4-design.md 7절.
 * 전 구간 32비트 정수. float 를 쓰지 않으므로 소프트웨어 부동소수점
 * 라이브러리(약 1.5~3KB Flash)가 링크되지 않는다.
 */

#include "classify.h"

/*
 * 방전 시간을 컨덕턴스로 바꾼다. 빛이 셀수록 t가 작고 G가 크다.
 * t == 0 은 타임아웃이며 "빛이 오지 않았다" = G 0 으로 본다.
 * t 최소값 1일 때 G = 1e9 이므로 세 채널 합의 최대는 3e9 < 4.29e9 (uint32 상한).
 */
static uint32_t conductance(uint32_t t) {
  if (t == 0) {
    return 0;
  }
  return CLASSIFY_K / t;
}

fingerprint_t classify_fingerprint(uint32_t t_dark, uint32_t t_r,
                                   uint32_t t_g, uint32_t t_b) {
  fingerprint_t fp;
  uint32_t t_ch[CLASSIFY_CHANNELS];
  uint32_t i[CLASSIFY_CHANNELS];
  uint32_t g_dark;
  uint32_t sum = 0;
  uint8_t k;

  t_ch[0] = t_r;
  t_ch[1] = t_g;
  t_ch[2] = t_b;

  g_dark = conductance(t_dark);

  /* 암전류 보정. 음수는 0으로 클램프한다. */
  for (k = 0; k < CLASSIFY_CHANNELS; k++) {
    uint32_t g = conductance(t_ch[k]);
    i[k] = (g > g_dark) ? (g - g_dark) : 0;
    sum += i[k];
  }

  if (sum < CLASSIFY_MIN_SIGNAL) {
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      fp.n[k] = 0;
    }
    fp.status = CLASSIFY_LOW_SIGNAL;
    return fp;
  }

  /*
   * 곱셈이 32비트에 들어갈 때까지 세 채널을 함께 우측 시프트한다.
   * 동일 배율이므로 채널 간 비율(=지문)은 보존된다.
   * 시프트 후 sum <= 4e6, i[k] <= sum 이므로 i[k]*1000 <= 4.0e9 < 4.29e9.
   */
  while (sum > CLASSIFY_SHIFT_LIMIT) {
    sum = 0;
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      i[k] >>= 1;
      sum += i[k];
    }
  }

  /* 시프트로 sum이 0이 되는 일은 없지만 0 나누기를 원천 차단한다. */
  if (sum == 0) {
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      fp.n[k] = 0;
    }
    fp.status = CLASSIFY_LOW_SIGNAL;
    return fp;
  }

  for (k = 0; k < CLASSIFY_CHANNELS; k++) {
    fp.n[k] = (uint16_t)((i[k] * CLASSIFY_NORM_SUM) / sum);
  }
  fp.status = CLASSIFY_OK;
  return fp;
}

classify_result_t classify_match(const fingerprint_t *fp,
                                 const uint16_t centroids[CLASSIFY_CLASSES][CLASSIFY_CHANNELS],
                                 uint32_t threshold_d2) {
  classify_result_t r;
  uint32_t best = 0xFFFFFFFFUL;
  int8_t   best_c = -1;
  uint8_t  c, k;

  r.cls  = -1;
  r.d2   = 0xFFFFFFFFUL;
  r.dist = 0;

  if (fp->status != CLASSIFY_OK) {
    return r;
  }

  for (c = 0; c < CLASSIFY_CLASSES; c++) {
    uint32_t d2 = 0;
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      int32_t diff = (int32_t)fp->n[k] - (int32_t)centroids[c][k];
      d2 += (uint32_t)(diff * diff);
    }
    if (d2 < best) {
      best   = d2;
      best_c = (int8_t)c;
    }
  }

  r.d2   = best;
  r.dist = classify_isqrt(best);
  r.cls  = (best <= threshold_d2) ? best_c : -1;
  return r;
}

uint16_t classify_isqrt(uint32_t v) {
  uint32_t x, y;

  if (v == 0) {
    return 0;
  }
  x = v;
  y = (x + 1) / 2;
  while (y < x) {
    x = y;
    y = (x + v / x) / 2;
  }
  return (uint16_t)x;
}
