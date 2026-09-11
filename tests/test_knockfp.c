/*
 * knockfp / classify 통합 단위 테스트.
 *
 * PC 용 C 컴파일러가 없는 환경이라, ATmega328P 용으로 빌드한 뒤 avr-gdb 의
 * 내장 시뮬레이터에서 실제로 실행한다. 결과는 전역 배열에 남기고 GDB 가
 * 읽어간다. (tools/run_tests.sh)
 *
 * 검사 항목은 "리듬 인증이 실제로 성립하는가"에 집중한다.
 *   - 템포가 달라도 같은 리듬이면 같은 지문이 나오는가 (정규화의 핵심)
 *   - 링잉/이상 입력이 걸러지는가
 *   - 32비트 곱셈이 넘치지 않는가 (시프트 경로)
 *   - 미등록 슬롯에 오인 매칭되지 않는가
 */

#include <stdint.h>

#include "knockfp.h"
#include "classify.h"

#define MAXCHK 48

/*
 * authstore.h 의 AUTH_THRESHOLD_MAX 와 같은 값. authstore.h 는 EEPROM
 * 레지스터에 의존하므로 순수 계산 테스트에 끌어들이지 않고 값만 복제한다.
 * 두 값이 어긋나면 아래 "임계값 상한" 검사가 의미를 잃으므로, 상한을 바꿀
 * 때는 여기도 함께 바꿀 것.
 */
#define AUTH_THRESHOLD_MAX  20000UL

/* GDB 가 읽어가는 결과 영역. 1 = PASS, 2 = FAIL */
volatile uint8_t g_outcome[MAXCHK];
volatile uint8_t g_nchk;
volatile uint8_t g_nfail;

static void check(int cond, const char *name) {
  (void)name;   /* 이름은 tools/run_tests.sh 가 소스에서 뽑아 쓴다 */
  if (g_nchk >= MAXCHK) {
    return;
  }
  g_outcome[g_nchk] = (uint8_t)(cond ? 1 : 2);
  if (!cond) {
    g_nfail++;
  }
  g_nchk++;
}

/* 밀리초를 틱으로 (1틱 = 500ns) */
static uint32_t ms(uint32_t v) {
  return v * KNOCKFP_TICKS_PER_MS;
}

static void set3(uint32_t *g, uint32_t a, uint32_t b, uint32_t c) {
  g[0] = ms(a);
  g[1] = ms(b);
  g[2] = ms(c);
}

/* ---- 1. 정규화 기본 동작 ---- */
static void test_uniform(void) {
  uint32_t g[CLASSIFY_CHANNELS];
  fingerprint_t fp;
  uint32_t sum;

  set3(g, 200, 200, 200);
  check(knockfp_make(g, &fp) == KNOCKFP_OK, "균등 리듬 - 상태 OK");
  check(fp.status == CLASSIFY_OK, "균등 리듬 - 지문 유효");
  check(fp.n[0] == fp.n[1] && fp.n[1] == fp.n[2], "균등 리듬 - 세 성분 동일");
  check(fp.n[0] >= 332 && fp.n[0] <= 334, "균등 리듬 - 각 성분 약 333");

  sum = (uint32_t)fp.n[0] + fp.n[1] + fp.n[2];
  check(sum >= 995 && sum <= 1000, "균등 리듬 - 합이 1000 근처");
}

/* ---- 2. 템포 불변성. 이 모듈의 존재 이유 ---- */
static void test_tempo_invariance(void) {
  uint32_t g[CLASSIFY_CHANNELS];
  fingerprint_t slow, fast, faster;

  set3(g, 200, 400, 200);
  (void)knockfp_make(g, &fast);

  set3(g, 300, 600, 300);   /* 같은 리듬을 1.5배 느리게 */
  (void)knockfp_make(g, &slow);

  set3(g, 100, 200, 100);   /* 같은 리듬을 2배 빠르게 */
  (void)knockfp_make(g, &faster);

  check(fast.n[0] == 250 && fast.n[1] == 500 && fast.n[2] == 250,
        "템포 불변 - 기준 지문 (250,500,250)");
  check(slow.n[0] == fast.n[0] && slow.n[1] == fast.n[1] &&
        slow.n[2] == fast.n[2], "템포 불변 - 1.5배 느려도 동일");
  check(faster.n[0] == fast.n[0] && faster.n[1] == fast.n[1] &&
        faster.n[2] == fast.n[2], "템포 불변 - 2배 빨라도 동일");
}

/* ---- 3. 이상 입력 배제 ---- */
static void test_reject(void) {
  uint32_t g[CLASSIFY_CHANNELS];
  fingerprint_t fp;

  set3(g, 30, 200, 200);    /* 40ms 미만 = 링잉 잔여 의심 */
  check(knockfp_make(g, &fp) == KNOCKFP_TOO_FAST, "배제 - 간격이 너무 짧음");
  check(fp.status == CLASSIFY_LOW_SIGNAL, "배제 - 짧은 간격은 지문 무효화");

  set3(g, 45, 45, 45);      /* 합 135ms < 150ms */
  check(knockfp_make(g, &fp) == KNOCKFP_TOO_SHORT, "배제 - 전체가 너무 짧음");

  set3(g, 2000, 2000, 2000); /* 합 6000ms > 5000ms */
  check(knockfp_make(g, &fp) == KNOCKFP_TOO_LONG, "배제 - 전체가 너무 김");
  check(fp.status == CLASSIFY_LOW_SIGNAL, "배제 - 긴 입력도 지문 무효화");

  set3(g, 40, 60, 60);      /* 경계: 간격 40ms 는 허용, 합 160ms 도 허용 */
  check(knockfp_make(g, &fp) == KNOCKFP_OK, "경계 - 하한 바로 위는 통과");
}

/* ---- 4. 32비트 오버플로 안전성 (시프트 경로) ---- */
static void test_overflow_path(void) {
  uint32_t g[CLASSIFY_CHANNELS];
  fingerprint_t fp;
  uint32_t sum;

  /*
   * 합 5000ms = 1e7 틱. KNOCKFP_SHIFT_LIMIT(4e6)을 넘으므로 우측 시프트
   * 경로를 탄다. 시프트를 하지 않으면 gap*1000 이 uint32 를 넘어 값이
   * 완전히 망가진다. 비율이 그대로 보존되는지 확인한다.
   */
  set3(g, 1000, 2000, 2000);
  check(knockfp_make(g, &fp) == KNOCKFP_OK, "오버플로 - 최대 길이 입력 통과");
  check(fp.n[0] == 200 && fp.n[1] == 400 && fp.n[2] == 400,
        "오버플로 - 시프트 후에도 비율 보존 (200,400,400)");

  sum = (uint32_t)fp.n[0] + fp.n[1] + fp.n[2];
  check(sum >= 995 && sum <= 1000, "오버플로 - 합이 여전히 1000 근처");
}

/* ---- 5. 등록 보조 함수 ---- */
static void test_enroll_helpers(void) {
  fingerprint_t s[3];
  uint16_t c[CLASSIFY_CHANNELS];
  uint32_t spread;

  s[0].n[0] = 250; s[0].n[1] = 500; s[0].n[2] = 250; s[0].status = CLASSIFY_OK;
  s[1].n[0] = 260; s[1].n[1] = 490; s[1].n[2] = 250; s[1].status = CLASSIFY_OK;
  s[2].n[0] = 240; s[2].n[1] = 510; s[2].n[2] = 250; s[2].status = CLASSIFY_OK;

  knockfp_centroid(s, 3, c);
  check(c[0] == 250 && c[1] == 500 && c[2] == 250, "등록 - 중심점 평균");

  /* 각 표본의 제곱거리: 0, (10^2 + 10^2) = 200, (10^2 + 10^2) = 200 */
  spread = knockfp_spread_d2(s, 3, c);
  check(spread == 200, "등록 - 최대 흩어짐 계산");
}

/* ---- 6. classify_match 통합 (실제 인증 판정 경로) ---- */
static void test_match(void) {
  uint16_t centroids[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];
  uint32_t g[CLASSIFY_CHANNELS];
  fingerprint_t fp;
  classify_result_t r;
  uint8_t u, k;

  /* 사용자 0만 등록. 나머지 슬롯은 authstore 가 0으로 채우는 상태를 재현. */
  for (u = 0; u < CLASSIFY_CLASSES; u++) {
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      centroids[u][k] = 0;
    }
  }
  centroids[0][0] = 250;
  centroids[0][1] = 500;
  centroids[0][2] = 250;

  /* 본인: 등록과 동일한 리듬 */
  set3(g, 200, 400, 200);
  (void)knockfp_make(g, &fp);
  r = classify_match(&fp, (const uint16_t (*)[CLASSIFY_CHANNELS])centroids,
                     6000UL);
  check(r.cls == 0, "판정 - 동일 리듬은 사용자 0으로 인식");
  check(r.d2 == 0, "판정 - 동일 리듬의 거리는 0");

  /* 본인: 템포만 다른 같은 리듬 (느리게) */
  set3(g, 340, 680, 340);
  (void)knockfp_make(g, &fp);
  r = classify_match(&fp, (const uint16_t (*)[CLASSIFY_CHANNELS])centroids,
                     6000UL);
  check(r.cls == 0, "판정 - 느린 템포의 같은 리듬도 통과");

  /* 타인: 순서를 알아도 리듬이 다른 경우 */
  set3(g, 200, 200, 400);
  (void)knockfp_make(g, &fp);
  r = classify_match(&fp, (const uint16_t (*)[CLASSIFY_CHANNELS])centroids,
                     6000UL);
  check(r.cls == -1, "판정 - 다른 리듬은 거부 (2FA 2단계 방어)");

  /*
   * 임계값 상한에서의 방어력.
   * (250,500,250) 과 (333,333,333) 의 제곱거리는 41,667 이다. 임계값 상한을
   * 이보다 크게 잡으면 명백히 다른 리듬까지 통과하게 된다. 상한이 실수로
   * 다시 커지면 여기서 잡힌다.
   */
  set3(g, 200, 200, 200);
  (void)knockfp_make(g, &fp);
  r = classify_match(&fp, (const uint16_t (*)[CLASSIFY_CHANNELS])centroids,
                     AUTH_THRESHOLD_MAX);
  check(r.cls == -1, "판정 - 임계값 상한에서도 다른 리듬은 거부");

  /*
   * 미등록 상태(전 슬롯이 0)에서는 어떤 리듬도 통과하면 안 된다.
   * 정규화된 지문은 원점에서 최소 333,000 만큼 떨어져 있으므로 구조적으로
   * 매칭될 수 없다는 것을 확인한다.
   */
  centroids[0][0] = 0;
  centroids[0][1] = 0;
  centroids[0][2] = 0;
  set3(g, 200, 400, 200);
  (void)knockfp_make(g, &fp);
  r = classify_match(&fp, (const uint16_t (*)[CLASSIFY_CHANNELS])centroids,
                     AUTH_THRESHOLD_MAX);
  check(r.cls == -1, "판정 - 미등록 상태에서는 어떤 리듬도 거부");

  centroids[0][0] = 250;
  centroids[0][1] = 500;
  centroids[0][2] = 250;

  /* 노크 실패로 무효화된 지문은 무조건 거부되어야 한다 */
  set3(g, 30, 200, 200);
  (void)knockfp_make(g, &fp);
  r = classify_match(&fp, (const uint16_t (*)[CLASSIFY_CHANNELS])centroids,
                     6000UL);
  check(r.cls == -1, "판정 - 무효 지문은 임계값과 무관하게 거부");
}

/* GDB 가 여기에 중단점을 건다. 이름을 바꾸면 tools/run_tests.sh 도 고칠 것. */
void test_done(void);
void test_done(void) {
  __asm__ __volatile__ ("nop");
}

int main(void) {
  g_nchk  = 0;
  g_nfail = 0;

  test_uniform();
  test_tempo_invariance();
  test_reject();
  test_overflow_path();
  test_enroll_helpers();
  test_match();

  test_done();
  for (;;) {
    ;
  }
}
