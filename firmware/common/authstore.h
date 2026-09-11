/*
 * authstore.h — 등록 정보와 실패 카운터를 EEPROM 에 보관한다.
 *
 * 기존 PEDD 프로젝트의 store.c 를 계승하되 두 가지를 더했다.
 *  1) 지식 인증(버튼 순서)까지 함께 저장한다.
 *  2) 전원을 껐다 켜도 지워지지 않는 실패 카운터를 둔다.
 *
 * 실패 카운터를 EEPROM 에 두는 이유 (보안 설계)
 *   카운터가 RAM 에만 있으면, 공격자는 몇 번 틀릴 때마다 전원을 뽑았다 꽂아
 *   카운터를 0으로 되돌리고 무제한으로 시도할 수 있다. 그래서 카운터는
 *   비휘발성이어야 하고, 더 중요하게는 **시도를 평가하기 전에 먼저 증가**
 *   시켜야 한다. 평가한 뒤에 올리면 "실패가 확정되기 직전에 전원을 끊는"
 *   방법으로 카운터를 회피할 수 있기 때문이다.
 *
 *   또한 카운터 자체가 EEPROM 기록 도중 전원이 끊겨 깨질 수 있으므로,
 *   값과 그 보수(complement)를 함께 저장해 무결성을 확인한다. 깨져 있으면
 *   "최대 실패"로 간주해 잠기는 쪽(fail-closed)으로 판단한다.
 *
 * avr-libc 의 eeprom_* 함수 대신 EECR/EEDR/EEARH/EEARL 을 직접 제어한다.
 */

#ifndef AUTHSTORE_H
#define AUTHSTORE_H

#include <stdint.h>
#include "classify.h"

/* 등록 가능한 사용자 수. classify_match() 를 그대로 쓰기 위해 클래스 수와 맞춘다. */
#define AUTH_USERS    CLASSIFY_CLASSES
/* 버튼 순서의 길이. 버튼 4개 x 4자리 = 256가지. */
#define AUTH_PIN_LEN  4

/* 미등록 슬롯 표시용. 버튼 번호는 0~3 이므로 0xFF 는 절대 일치하지 않는다. */
#define AUTH_PIN_EMPTY  0xFF

/*
 * 인증 임계값(제곱거리) 한 사용자 몫의 허용 범위.
 *
 * 지문은 세 성분의 합이 CLASSIFY_NORM_SUM(=1000)으로 정규화되어 있으므로,
 * 임계값의 제곱근이 그대로 "허용 반경"이 된다.
 *   MAX = 20000 -> 반경 141, 성분당 약 8% 의 변동까지 허용
 * 사람이 같은 리듬을 다시 칠 때의 변동은 성분당 3~5% 수준이므로 충분한
 * 여유이면서, 명백히 다른 리듬은 확실히 배제된다.
 *   예: (250,500,250) 과 (333,333,333) 의 제곱거리는 41,667 로 상한을 넘는다.
 *
 * 상한을 이보다 크게 잡으면 리듬이 들쭉날쭉한 사용자를 등록해 주는 대신
 * 타인도 함께 통과하게 되므로, 그런 등록은 아예 거부하는 편이 안전하다.
 * (main.c 의 enroll_commit() 이 이 상한으로 등록을 거부한다)
 *
 * 최종값은 실험 3 - 리듬 재현성 측정과 실험 4 - 타인 모사 시도에서 얻은
 * FRR/FAR 곡선을 보고 확정한다. 여기 값은 그 실험의 출발점이다.
 *
 * [주의] 임계값은 사용자마다 따로 저장한다(threshold_d2[AUTH_USERS]).
 * 한 사람의 재현성에서 유도한 값을 전원이 공유하면, 새 사용자를 등록할
 * 때마다 이미 등록된 다른 사용자의 임계값까지 함께 바뀌어 버린다
 * (FRR/FAR 이 등록 순서에 따라 흔들리는 결함이었다). AUTH_THRESHOLD_MIN/MAX
 * 는 그 개별 값 하나하나에 적용되는 한계일 뿐이다.
 */
#define AUTH_THRESHOLD_MIN  2000UL
#define AUTH_THRESHOLD_MAX  20000UL

/* 연속 실패 허용 횟수와 초과 시 강제 대기 시간 */
#define AUTH_FAIL_MAX       5
#define AUTH_LOCKOUT_MS     30000UL

/* ---- EEPROM 배치. 총 0x00~0x29 (42바이트) + 카운터 2바이트 ---- */
#define AUTH_ADDR_MAGIC      0x00  /* 2 */
#define AUTH_ADDR_VERSION    0x02  /* 1 */
#define AUTH_ADDR_USERS      0x03  /* 1 */
#define AUTH_ADDR_PINS       0x04  /* AUTH_USERS * AUTH_PIN_LEN = 12 */
#define AUTH_ADDR_CENTROIDS  0x10  /* AUTH_USERS * CLASSIFY_CHANNELS * 2 = 18 */
#define AUTH_ADDR_THRESHOLD  0x22  /* 사용자별 저장. AUTH_USERS * 2 = 6 */
#define AUTH_ADDR_CHECKSUM   0x28  /* 2. 여기까지가 체크섬 대상 */

/*
 * 실패 카운터는 체크섬 범위 밖에 둔다. 인증 시도마다 갱신되는 값이라
 * 체크섬 안에 넣으면 등록 정보 전체를 매번 다시 써야 하고, EEPROM 수명
 * (10만 회)을 등록 정보 영역까지 함께 갉아먹기 때문이다.
 */
#define AUTH_ADDR_FAIL       0x30  /* 1 */
#define AUTH_ADDR_FAIL_INV   0x31  /* 1 */

#define AUTH_MAGIC    0x4B32u   /* 'K2' */
#define AUTH_VERSION  1

typedef struct {
  uint8_t  users;                                        /* 등록된 사용자 수 */
  uint8_t  pin[AUTH_USERS][AUTH_PIN_LEN];
  uint16_t centroid[AUTH_USERS][CLASSIFY_CHANNELS];
  uint32_t threshold_d2[AUTH_USERS];  /* 사용자별 임계값. 공용 아님 */
} auth_db_t;

/*
 * 등록 정보를 읽는다. 매직·버전·사용자 수·체크섬이 모두 맞아야 1을 반환한다.
 * 공장 출하 EEPROM 은 전부 0xFF 라 자연스럽게 무효로 걸러진다.
 * 0을 반환하면 db 는 "사용자 0명"으로 안전하게 초기화된다.
 */
uint8_t authstore_load(auth_db_t *db);

/* 등록 정보 전체를 기록한다. 체크섬은 마지막에 쓴다. */
void authstore_save(const auth_db_t *db);

/* 매직을 지워 "미등록" 상태로 되돌린다. */
void authstore_erase(void);

/*
 * 실패 카운터를 읽는다. 값과 보수가 어긋나 있으면(기록 중 전원 차단 등)
 * AUTH_FAIL_MAX 를 반환해 잠기는 쪽으로 판단한다.
 */
uint8_t authstore_fail_get(void);

/* 실패 카운터를 기록한다. 값 -> 보수 순서로 쓴다. */
void authstore_fail_set(uint8_t v);

#endif /* AUTHSTORE_H */
