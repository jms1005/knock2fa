#!/bin/sh
# knockfp / classify 단위 테스트를 avr-gdb 내장 시뮬레이터에서 실행한다.
#
# PC 용 C 컴파일러가 없는 환경이므로, 테스트도 ATmega328P 코드로 빌드해서
# 시뮬레이터 위에서 진짜로 돌린다. 결과는 전역 배열 g_outcome[] 에 남고
# GDB 가 그것을 읽어 출력한다.
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/build"
mkdir -p "$OUT"

avr-gcc -mmcu=atmega328p -DF_CPU=16000000UL -O1 -g -std=gnu99 \
        -Wall -Wextra -Werror \
        -I"$ROOT/firmware/common" \
        -o "$OUT/test_knockfp.elf" \
        "$ROOT/tests/test_knockfp.c" \
        "$ROOT/firmware/common/knockfp.c" \
        "$ROOT/firmware/common/classify.c"

avr-gdb --batch -q \
  -ex "target sim" \
  -ex "load" \
  -ex "break test_done" \
  -ex "run" \
  -ex "printf \"NCHK %d\n\", g_nchk" \
  -ex "printf \"NFAIL %d\n\", g_nfail" \
  -ex "print/d g_outcome" \
  "$OUT/test_knockfp.elf" > "$OUT/gdb_out.txt" 2>&1 || true

python "$ROOT/tools/test_report.py" "$ROOT/tests/test_knockfp.c" "$OUT/gdb_out.txt"
