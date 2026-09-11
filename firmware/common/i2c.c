/*
 * i2c.c — TWI 마스터
 */

#include <avr/io.h>

#include "i2c.h"

/*
 * SCL = F_CPU / (16 + 2 * TWBR * 4^TWPS)
 * TWPS = 0, TWBR = 12 -> 16000000 / (16 + 24) = 400kHz
 * SSD1306은 400kHz를 지원한다. 화면 갱신 속도에 직접 영향을 준다.
 */
#define I2C_TWBR_400K  12

/* TWINT 대기 상한. 슬레이브가 없을 때 무한 대기를 막는다. */
#define I2C_GUARD  20000u

static uint8_t wait_twint(void) {
  uint16_t guard = 0;
  while (!(TWCR & (1 << TWINT))) {
    if (++guard >= I2C_GUARD) {
      return 0;
    }
  }
  return 1;
}

void i2c_init(void) {
  TWSR = 0;                 /* 프리스케일러 1 */
  TWBR = I2C_TWBR_400K;
  TWCR = (1 << TWEN);
}

uint8_t i2c_start(uint8_t addr7, uint8_t read) {
  uint8_t status;

  TWCR = (1 << TWINT) | (1 << TWSTA) | (1 << TWEN);
  if (!wait_twint()) {
    return 0;
  }
  status = (uint8_t)(TWSR & 0xF8);
  /* 0x08 = START 전송됨, 0x10 = 반복 START 전송됨 */
  if (status != 0x08 && status != 0x10) {
    return 0;
  }

  TWDR = (uint8_t)((addr7 << 1) | (read ? 1 : 0));
  TWCR = (1 << TWINT) | (1 << TWEN);
  if (!wait_twint()) {
    return 0;
  }
  status = (uint8_t)(TWSR & 0xF8);
  /* 0x18 = SLA+W 에 ACK, 0x40 = SLA+R 에 ACK */
  return (uint8_t)((status == 0x18 || status == 0x40) ? 1 : 0);
}

uint8_t i2c_write(uint8_t data) {
  TWDR = data;
  TWCR = (1 << TWINT) | (1 << TWEN);
  if (!wait_twint()) {
    return 0;
  }
  /* 0x28 = 데이터 전송 후 ACK */
  return (uint8_t)(((TWSR & 0xF8) == 0x28) ? 1 : 0);
}

void i2c_stop(void) {
  uint16_t guard = 0;
  TWCR = (1 << TWINT) | (1 << TWSTO) | (1 << TWEN);
  /* STOP 완료는 TWSTO 가 자동으로 내려가는 것으로 확인한다. */
  while (TWCR & (1 << TWSTO)) {
    if (++guard >= I2C_GUARD) {
      return;
    }
  }
}
