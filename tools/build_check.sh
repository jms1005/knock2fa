#!/bin/sh
# avr-gcc 로 전체 펌웨어를 빌드하고 메모리 사용량을 출력한다.
# Microchip Studio 없이도 문법/타입 오류를 잡기 위한 검증용 스크립트다.
# 경고를 오류로 승격(-Werror)시켜, 경고가 하나라도 있으면 빌드가 실패한다.
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/build"
mkdir -p "$OUT"

CFLAGS="-mmcu=atmega328p -DF_CPU=16000000UL -Os -std=gnu99 -funsigned-char
        -funsigned-bitfields -fpack-struct -fshort-enums -ffunction-sections
        -fdata-sections -Wall -Wextra -Werror -Wundef -Wshadow
        -Wstrict-prototypes -Wmissing-prototypes -Wredundant-decls
        -I$ROOT/firmware/common"

SRC="$ROOT/firmware/knock2fa/main.c
     $ROOT/firmware/common/knock.c
     $ROOT/firmware/common/knockfp.c
     $ROOT/firmware/common/keypad.c
     $ROOT/firmware/common/timebase.c
     $ROOT/firmware/common/authstore.c
     $ROOT/firmware/common/classify.c
     $ROOT/firmware/common/i2c.c
     $ROOT/firmware/common/ssd1306.c
     $ROOT/firmware/common/uart.c"

# shellcheck disable=SC2086
avr-gcc $CFLAGS -Wl,--gc-sections -o "$OUT/knock2fa.elf" $SRC
avr-objcopy -O ihex -R .eeprom "$OUT/knock2fa.elf" "$OUT/knock2fa.hex"

echo ""
echo "=== 메모리 사용량 (ATmega328P: Flash 32768 B / SRAM 2048 B) ==="
avr-size -A "$OUT/knock2fa.elf" | python "$ROOT/tools/size_report.py"
