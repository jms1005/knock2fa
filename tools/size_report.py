#!/usr/bin/env python3
"""avr-size -A 출력을 받아 ATmega328P 기준 사용률을 표로 낸다.

  Flash = .text + .data   (초기값이 있는 전역변수는 Flash 에도 원본이 실린다)
  SRAM  = .data + .bss    (부팅 시 .data 가 SRAM 으로 복사되고 .bss 는 0으로 채워진다)
"""
import sys

FLASH_TOTAL = 32768
SRAM_TOTAL = 2048

sec = {}
for line in sys.stdin:
    parts = line.split()
    if len(parts) >= 2 and parts[0].startswith('.'):
        try:
            sec[parts[0]] = int(parts[1])
        except ValueError:
            pass

text = sec.get('.text', 0)
data = sec.get('.data', 0)
bss = sec.get('.bss', 0)
noinit = sec.get('.noinit', 0)

flash = text + data
sram = data + bss + noinit

print(f"  .text {text:6d} B   .data {data:5d} B   .bss {bss:5d} B")
print(f"  Flash {flash:6d} / {FLASH_TOTAL} B  ({flash*100.0/FLASH_TOTAL:5.1f} %)")
print(f"  SRAM  {sram:6d} / {SRAM_TOTAL} B  ({sram*100.0/SRAM_TOTAL:5.1f} %)")
