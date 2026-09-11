/*
 * knockfp.c — 템포 정규화 지문 (구현)
 *
 * 전 구간 32비트 정수. float 를 쓰지 않으므로 소프트웨어 부동소수점
 * 라이브러리(약 1.5~3KB Flash)가 링크되지 않는다. classify.c 와 같은 원칙.
 */

#include "knockfp.h"

static void fp_zero(fingerprint_t *fp) {
  uint8_t k;
  for (k = 0; k < CLASSIFY_CHANNELS; k++) {
    fp->n[k] = 0;
  }
  fp->status = CLASSIFY_LOW_SIGNAL;
}

knockfp_status_t knockfp_make(const uint32_t gaps[CLASSIFY_CHANNELS],
                              fingerprint_t *fp) {
  uint32_t g[CLASSIFY_CHANNELS];
  uint32_t total = 0;
  uint8_t  k;

  for (k = 0; k < CLASSIFY_CHANNELS; k++) {
    if (gaps[k] < KNOCKFP_MIN_GAP) {
      fp_zero(fp);
      return KNOCKFP_TOO_FAST;
    }
    g[k] = gaps[k];
    total += g[k];
  }

  if (total < KNOCKFP_MIN_TOTAL) {
    fp_zero(fp);
    return KNOCKFP_TOO_SHORT;
  }
  if (total > KNOCKFP_MAX_TOTAL) {
    fp_zero(fp);
    return KNOCKFP_TOO_LONG;
  }

  /*
   * 곱셈이 32비트에 들어갈 때까지 전 성분을 함께 우측 시프트한다.
   * 동일 배율이므로 성분 간 비율(= 리듬의 형태)은 보존된다.
   *
   * 상한 확인: KNOCKFP_MAX_TOTAL = 5000ms = 1e7 틱이므로 시프트가 한 번은
   * 필요할 수 있다. 시프트 후 total <= 4e6, g[k] <= total 이므로
   * g[k] * 1000 <= 4.0e9 < 4.294e9 로 uint32 안에 들어간다.
   */
  while (total > KNOCKFP_SHIFT_LIMIT) {
    total = 0;
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      g[k] >>= 1;
      total += g[k];
    }
  }

  /* MIN_TOTAL 검사를 통과했으므로 0이 될 수 없지만, 0 나누기를 원천 차단한다. */
  if (total == 0) {
    fp_zero(fp);
    return KNOCKFP_TOO_SHORT;
  }

  for (k = 0; k < CLASSIFY_CHANNELS; k++) {
    fp->n[k] = (uint16_t)((g[k] * CLASSIFY_NORM_SUM) / total);
  }
  fp->status = CLASSIFY_OK;
  return KNOCKFP_OK;
}

void knockfp_centroid(const fingerprint_t *samples, uint8_t n_samples,
                      uint16_t out[CLASSIFY_CHANNELS]) {
  uint8_t  i, k;
  uint32_t acc[CLASSIFY_CHANNELS];

  for (k = 0; k < CLASSIFY_CHANNELS; k++) {
    acc[k] = 0;
  }
  if (n_samples == 0) {
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      out[k] = 0;
    }
    return;
  }

  for (i = 0; i < n_samples; i++) {
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      acc[k] += samples[i].n[k];
    }
  }
  for (k = 0; k < CLASSIFY_CHANNELS; k++) {
    out[k] = (uint16_t)(acc[k] / n_samples);
  }
}

uint32_t knockfp_spread_d2(const fingerprint_t *samples, uint8_t n_samples,
                           const uint16_t centroid[CLASSIFY_CHANNELS]) {
  uint32_t worst = 0;
  uint8_t  i, k;

  for (i = 0; i < n_samples; i++) {
    uint32_t d2 = 0;
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      int32_t diff = (int32_t)samples[i].n[k] - (int32_t)centroid[k];
      d2 += (uint32_t)(diff * diff);
    }
    if (d2 > worst) {
      worst = d2;
    }
  }
  return worst;
}
