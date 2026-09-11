/*
 * i2c.h — TWI(I2C) 마스터 송신 전용
 *
 * TWBR/TWCR/TWDR/TWSR 레지스터를 직접 제어한다.
 * 모든 함수는 유한 시간 안에 반환한다. 슬레이브가 없어도 멈추지 않아야
 * 측정과 UART 로깅이 계속될 수 있다 (스펙 9절).
 */

#ifndef I2C_H
#define I2C_H

#include <stdint.h>

void    i2c_init(void);
uint8_t i2c_start(uint8_t addr7, uint8_t read);
uint8_t i2c_write(uint8_t data);
void    i2c_stop(void);

#endif /* I2C_H */
