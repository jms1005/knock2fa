/*
 * uart.c — UART 송신 (구현)
 *
 * 요강 대응: 라이브러리 대신 UBRR0 / UCSR0B / UCSR0C / UDR0 레지스터를
 *           직접 제어한다. (운영설명 PDF 1-라)
 */

#ifndef F_CPU
#define F_CPU 16000000UL
#endif

#include <avr/io.h>
#include "uart.h"

/*
 * 통신 속도 38400 bps.
 * UBRR = F_CPU / (16 x BAUD) - 1 = 16000000 / (16 x 38400) - 1 = 25.04 -> 25
 * 실제 속도 오차 0.2%로, 수신 측이 허용하는 범위(약 2%) 안에 충분히 든다.
 * 115200을 쓰면 오차가 3.5%까지 커져 문자가 깨지므로 채택하지 않았다.
 */
#define UART_BAUD 38400UL
#define UART_UBRR ((F_CPU / (16UL * UART_BAUD)) - 1)

void uart_init(void) {
  /* 통신 속도 설정 — 상위 바이트를 먼저 쓴다 */
  UBRR0H = (uint8_t)(UART_UBRR >> 8);
  UBRR0L = (uint8_t)(UART_UBRR);

  /* 송신부만 활성화. 수신은 쓰지 않으므로 RXEN0를 켜지 않는다. */
  UCSR0B = (1 << TXEN0);

  /* 8비트 데이터, 패리티 없음, 정지 비트 1 (8N1) */
  UCSR0C = (1 << UCSZ01) | (1 << UCSZ00);
}

void uart_putc(char c) {
  /* UDRE0가 1이 될 때까지 대기 — 송신 버퍼가 비어야 다음 문자를 넣을 수 있다 */
  while (!(UCSR0A & (1 << UDRE0))) {
    ;
  }
  UDR0 = c;
}

void uart_puts(const char *s) {
  while (*s) {
    uart_putc(*s++);
  }
}

void uart_put_u32(uint32_t v) {
  /* 32비트 부호 없는 정수의 최대 자릿수는 10자리 */
  char buf[11];
  uint8_t i = 0;

  if (v == 0) {
    uart_putc('0');
    return;
  }

  /* 낮은 자리부터 추출되므로 역순으로 담았다가 뒤집어 출력한다 */
  while (v > 0) {
    buf[i++] = (char)('0' + (v % 10));
    v /= 10;
  }
  while (i > 0) {
    uart_putc(buf[--i]);
  }
}

void uart_newline(void) {
  uart_putc('\r');
  uart_putc('\n');
}
