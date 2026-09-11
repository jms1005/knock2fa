/*
 * ssd1306.c — OLED 드라이버
 */

#include <avr/pgmspace.h>

#include "ssd1306.h"
#include "i2c.h"
#include "font6x8.h"

#define CTRL_CMD   0x00
#define CTRL_DATA  0x40

/* 초기화에 실패하면 이후 모든 출력을 건너뛴다. */
static uint8_t g_ready = 0;

/* 데이터시트 권장 초기화 시퀀스 (128x64) */
static const uint8_t INIT_SEQ[] PROGMEM = {
  0xAE,        /* 디스플레이 끄기 */
  0xD5, 0x80,  /* 클럭 분주 */
  0xA8, 0x3F,  /* 멀티플렉스 비율 = 64 */
  0xD3, 0x00,  /* 표시 오프셋 없음 */
  0x40,        /* 시작 라인 0 */
  0x8D, 0x14,  /* 차지 펌프 켜기 (모듈이 자체 승압) */
  0x20, 0x02,  /* 페이지 주소 모드 */
  0xA1,        /* 좌우 반전 - 일반적인 모듈 배치 기준 */
  0xC8,        /* 상하 반전 */
  0xDA, 0x12,  /* COM 핀 배치 */
  0x81, 0x7F,  /* 밝기 */
  0xD9, 0xF1,  /* 프리차지 */
  0xDB, 0x40,  /* VCOMH */
  0xA4,        /* RAM 내용 표시 */
  0xA6,        /* 정상 표시 (반전 아님) */
  0xAF         /* 디스플레이 켜기 */
};

static uint8_t cmd(uint8_t c) {
  if (!i2c_start(SSD1306_ADDR, 0)) {
    return 0;
  }
  if (!i2c_write(CTRL_CMD)) {
    i2c_stop();
    return 0;
  }
  if (!i2c_write(c)) {
    i2c_stop();
    return 0;
  }
  i2c_stop();
  return 1;
}

/* 커서를 (page, 픽셀 x) 로 옮긴다. */
static uint8_t set_pos(uint8_t page, uint8_t x) {
  if (!cmd((uint8_t)(0xB0 | (page & 0x07)))) {
    return 0;
  }
  if (!cmd((uint8_t)(0x00 | (x & 0x0F)))) {          /* 하위 니블 */
    return 0;
  }
  return cmd((uint8_t)(0x10 | ((x >> 4) & 0x0F)));   /* 상위 니블 */
}

void ssd1306_clear(void) {
  uint8_t page, i;

  if (!g_ready) {
    return;
  }
  for (page = 0; page < SSD1306_PAGES; page++) {
    if (!set_pos(page, 0)) {
      return;
    }
    if (!i2c_start(SSD1306_ADDR, 0)) {
      return;
    }
    if (!i2c_write(CTRL_DATA)) {
      i2c_stop();
      return;
    }
    for (i = 0; i < SSD1306_COLS; i++) {
      if (!i2c_write(0x00)) {
        break;
      }
    }
    i2c_stop();
  }
}

uint8_t ssd1306_init(void) {
  uint8_t i;

  g_ready = 0;
  i2c_init();
  for (i = 0; i < sizeof(INIT_SEQ); i++) {
    if (!cmd(pgm_read_byte(&INIT_SEQ[i]))) {
      return 0;
    }
  }
  g_ready = 1;
  ssd1306_clear();
  return 1;
}

/*
 * 문자열 출력 공통 구현.
 * from_pgm 이 1이면 s 는 Flash(PROGMEM) 주소, 0이면 SRAM 주소다.
 */
static void puts_impl(uint8_t page, uint8_t col, const char *s, uint8_t from_pgm) {
  uint8_t x;

  if (!g_ready || page >= SSD1306_PAGES) {
    return;
  }
  x = (uint8_t)(col * FONT_WIDTH);
  if (!set_pos(page, x)) {
    return;
  }
  if (!i2c_start(SSD1306_ADDR, 0)) {
    return;
  }
  if (!i2c_write(CTRL_DATA)) {
    i2c_stop();
    return;
  }
  while ((uint16_t)(x + FONT_WIDTH) <= SSD1306_COLS) {
    uint8_t c = from_pgm ? (uint8_t)pgm_read_byte(s) : (uint8_t)*s;
    uint8_t i;
    if (c == 0) {
      break;
    }
    s++;
    /* 폰트 범위 밖(소문자 등)은 공백으로 대체한다. */
    if (c < FONT_FIRST_CHAR || c > FONT_LAST_CHAR) {
      c = ' ';
    }
    for (i = 0; i < FONT_WIDTH; i++) {
      if (!i2c_write(pgm_read_byte(&FONT6X8[c - FONT_FIRST_CHAR][i]))) {
        i2c_stop();
        return;
      }
    }
    x = (uint8_t)(x + FONT_WIDTH);
  }
  i2c_stop();
}

void ssd1306_puts(uint8_t page, uint8_t col, const char *s) {
  puts_impl(page, col, s, 0);
}

void ssd1306_puts_p(uint8_t page, uint8_t col, const char *s) {
  puts_impl(page, col, s, 1);
}
