/*
 * ssd1306.h — 0.96" 128x64 OLED 텍스트 출력
 *
 * 프레임버퍼를 쓰지 않는다. 128x64/8 = 1024바이트로 SRAM 2KB의 절반을
 * 차지하기 때문이다. 대신 페이지 주소 모드로 화면에 직접 쓴다.
 */

#ifndef SSD1306_H
#define SSD1306_H

#include <stdint.h>

#define SSD1306_ADDR      0x3C  /* 모듈에 따라 0x3D 인 제품도 있다 */
#define SSD1306_PAGES     8     /* 세로 8줄 */
#define SSD1306_COLS      128
#define SSD1306_TEXT_COLS 21    /* 128 / 6 */

/* 초기화. OLED가 응답하지 않으면 0을 반환하고, 이후 호출은 조용히 무시된다. */
uint8_t ssd1306_init(void);

void ssd1306_clear(void);

/* page 0~7, col 0~20 (문자 단위). 화면 밖은 잘린다. */
void ssd1306_puts(uint8_t page, uint8_t col, const char *s);

/*
 * PSTR() 로 감싼 Flash 상주 문자열을 출력한다.
 * AVR 은 일반 문자열 리터럴을 부팅 시 SRAM 으로 복사하므로, 화면 문구처럼
 * 개수가 많은 상수는 반드시 이쪽을 써야 한다. SRAM 2KB 가 금방 찬다.
 */
void ssd1306_puts_p(uint8_t page, uint8_t col, const char *s);

#endif /* SSD1306_H */
