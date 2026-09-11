/*
 * authstore.c — EEPROM 접근 (레지스터 직접 제어)
 */

#include <avr/io.h>
#include <util/atomic.h>

#include "authstore.h"

static uint8_t ee_read(uint16_t addr) {
  /* 이전 쓰기가 끝날 때까지 대기 */
  while (EECR & (1 << EEPE)) {
    ;
  }
  EEARH = (uint8_t)(addr >> 8);
  EEARL = (uint8_t)(addr & 0xFF);
  EECR |= (1 << EERE);
  return EEDR;
}

static void ee_write(uint16_t addr, uint8_t value) {
  while (EECR & (1 << EEPE)) {
    ;
  }
  EEARH = (uint8_t)(addr >> 8);
  EEARL = (uint8_t)(addr & 0xFF);

  /*
   * 값이 이미 같으면 쓰지 않는다. EEPROM 은 셀당 약 10만 회의 수명이 있고,
   * 실패 카운터처럼 자주 갱신되는 바이트가 있으므로 불필요한 기록을 줄인다.
   * 위에서 주소를 이미 세팅했으므로 EERE 만 세우면 현재 값을 읽을 수 있다.
   */
  EECR |= (1 << EERE);
  if (EEDR == value) {
    return;
  }

  EEDR = value;
  /*
   * EEMPE 를 세운 뒤 4클럭 안에 EEPE 를 세워야 한다.
   * 인터럽트가 끼어들면 이 창을 놓치므로 원자 구간으로 감싼다.
   */
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    EECR |= (1 << EEMPE);
    EECR |= (1 << EEPE);
  }
}

static uint16_t ee_read16(uint16_t addr) {
  return (uint16_t)((uint16_t)ee_read(addr) |
                    ((uint16_t)ee_read((uint16_t)(addr + 1)) << 8));
}

static void ee_write16(uint16_t addr, uint16_t value) {
  ee_write(addr, (uint8_t)(value & 0xFF));
  ee_write((uint16_t)(addr + 1), (uint8_t)(value >> 8));
}

/* 체크섬 대상 구간의 단순 합. 상위 비트는 버린다. */
static uint16_t checksum_stored(void) {
  uint16_t sum = 0;
  uint16_t a;

  for (a = 0; a < AUTH_ADDR_CHECKSUM; a++) {
    sum = (uint16_t)(sum + ee_read(a));
  }
  return sum;
}

static void db_clear(auth_db_t *db) {
  uint8_t u, k;

  db->users = 0;
  for (u = 0; u < AUTH_USERS; u++) {
    db->threshold_d2[u] = AUTH_THRESHOLD_MIN;
    for (k = 0; k < AUTH_PIN_LEN; k++) {
      db->pin[u][k] = AUTH_PIN_EMPTY;
    }
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      /*
       * 미등록 슬롯의 중심점은 0으로 둔다. 정상 지문은 세 성분의 합이
       * CLASSIFY_NORM_SUM(=1000) 이므로 원점까지의 제곱거리는 최소
       * 1000^2/3 ~ 333,000 이 되어, 어떤 임계값(최대 20,000)으로도
       * 미등록 슬롯에 오인 매칭될 수 없다.
       */
      db->centroid[u][k] = 0;
    }
  }
}

uint8_t authstore_load(auth_db_t *db) {
  uint8_t  u, k;
  uint16_t addr;

  db_clear(db);

  if (ee_read16(AUTH_ADDR_MAGIC) != AUTH_MAGIC) {
    return 0;
  }
  if (ee_read(AUTH_ADDR_VERSION) != AUTH_VERSION) {
    return 0;
  }
  if (ee_read(AUTH_ADDR_USERS) == 0 || ee_read(AUTH_ADDR_USERS) > AUTH_USERS) {
    return 0;
  }
  if (ee_read16(AUTH_ADDR_CHECKSUM) != checksum_stored()) {
    return 0;
  }

  db->users = ee_read(AUTH_ADDR_USERS);

  addr = AUTH_ADDR_PINS;
  for (u = 0; u < AUTH_USERS; u++) {
    for (k = 0; k < AUTH_PIN_LEN; k++) {
      db->pin[u][k] = ee_read(addr);
      addr = (uint16_t)(addr + 1);
    }
  }

  addr = AUTH_ADDR_CENTROIDS;
  for (u = 0; u < AUTH_USERS; u++) {
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      db->centroid[u][k] = ee_read16(addr);
      addr = (uint16_t)(addr + 2);
    }
  }

  addr = AUTH_ADDR_THRESHOLD;
  for (u = 0; u < AUTH_USERS; u++) {
    db->threshold_d2[u] = ee_read16(addr);
    addr = (uint16_t)(addr + 2);
  }
  return 1;
}

void authstore_save(const auth_db_t *db) {
  uint8_t  u, k;
  uint16_t addr;

  ee_write16(AUTH_ADDR_MAGIC, AUTH_MAGIC);
  ee_write(AUTH_ADDR_VERSION, AUTH_VERSION);
  ee_write(AUTH_ADDR_USERS,   db->users);

  addr = AUTH_ADDR_PINS;
  for (u = 0; u < AUTH_USERS; u++) {
    for (k = 0; k < AUTH_PIN_LEN; k++) {
      ee_write(addr, db->pin[u][k]);
      addr = (uint16_t)(addr + 1);
    }
  }

  addr = AUTH_ADDR_CENTROIDS;
  for (u = 0; u < AUTH_USERS; u++) {
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      ee_write16(addr, db->centroid[u][k]);
      addr = (uint16_t)(addr + 2);
    }
  }

  addr = AUTH_ADDR_THRESHOLD;
  for (u = 0; u < AUTH_USERS; u++) {
    uint32_t th = db->threshold_d2[u];

    if (th < AUTH_THRESHOLD_MIN) {
      th = AUTH_THRESHOLD_MIN;
    }
    if (th > AUTH_THRESHOLD_MAX) {
      th = AUTH_THRESHOLD_MAX;
    }
    ee_write16(addr, (uint16_t)th);
    addr = (uint16_t)(addr + 2);
  }

  /* 체크섬은 나머지를 모두 기록한 뒤 마지막에 쓴다. */
  ee_write16(AUTH_ADDR_CHECKSUM, checksum_stored());
}

void authstore_erase(void) {
  ee_write16(AUTH_ADDR_MAGIC, 0xFFFF);
}

uint8_t authstore_fail_get(void) {
  uint8_t v   = ee_read(AUTH_ADDR_FAIL);
  uint8_t inv = ee_read(AUTH_ADDR_FAIL_INV);

  /*
   * 공장 출하 상태의 EEPROM 은 전 바이트가 0xFF 다. 이것은 손상이 아니라
   * "아직 한 번도 쓴 적 없음"이므로 실패 0회로 본다. 이 예외가 없으면 새
   * 칩을 처음 켤 때마다 30초 잠금 화면부터 보게 된다.
   */
  if (v == 0xFF && inv == 0xFF) {
    return 0;
  }

  /*
   * 그 밖에 값과 보수가 맞지 않는다면 기록 도중 전원이 끊긴 것이다.
   * "모르는 상태"이므로 최대 실패로 간주해 잠근다. 이렇게 해야 전원을 끊어
   * 카운터를 무력화하려는 시도가 오히려 잠금으로 이어진다.
   */
  if ((uint8_t)(v ^ inv) != 0xFF) {
    return AUTH_FAIL_MAX;
  }
  if (v > AUTH_FAIL_MAX) {
    return AUTH_FAIL_MAX;
  }
  return v;
}

void authstore_fail_set(uint8_t v) {
  if (v > AUTH_FAIL_MAX) {
    v = AUTH_FAIL_MAX;
  }
  /*
   * 값을 먼저, 보수를 나중에 쓴다. 두 기록 사이에 전원이 끊기면 다음 부팅에서
   * 무결성 검사가 깨져 authstore_fail_get() 이 AUTH_FAIL_MAX 를 반환한다.
   * 즉 어떤 중단 시점에서도 카운터가 낮아지는 방향으로는 깨지지 않는다.
   */
  ee_write(AUTH_ADDR_FAIL, v);
  ee_write(AUTH_ADDR_FAIL_INV, (uint8_t)~v);
}
