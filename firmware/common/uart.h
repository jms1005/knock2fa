/*
 * uart.h — UART 송신 (인터페이스)
 *
 * 측정 원시 데이터를 PC로 로깅하는 용도. (계획서 6.4절 5항)
 */

#ifndef UART_H
#define UART_H

#include <stdint.h>

void uart_init(void);
void uart_putc(char c);
void uart_puts(const char *s);
void uart_put_u32(uint32_t v);   /* 부호 없는 10진수 출력 */
void uart_newline(void);

#endif /* UART_H */
