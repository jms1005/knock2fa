#!/usr/bin/env python3
"""avr-gdb 시뮬레이터 실행 결과를 사람이 읽을 표로 바꾼다.

검사 이름은 테스트 소스의 check(..., "이름") 에서 순서대로 뽑아 쓴다.
그래야 소스와 리포트가 어긋나지 않는다.
"""
import io
import re
import sys

if len(sys.argv) != 3:
    sys.stderr.write("usage: test_report.py <test.c> <gdb_out.txt>\n")
    sys.exit(2)

src = io.open(sys.argv[1], encoding="utf-8").read()
out = io.open(sys.argv[2], encoding="utf-8", errors="replace").read()

# check(...) 마지막 인자의 문자열 리터럴을 순서대로 수집
names = re.findall(r'check\([^;]*?"((?:[^"\\]|\\.)*)"\s*\)\s*;', src, re.S)

m_n = re.search(r"NCHK (\d+)", out)
m_f = re.search(r"NFAIL (\d+)", out)
m_o = re.search(r"\$\d+ = \{([^}]*)\}", out)

if not (m_n and m_f and m_o):
    sys.stderr.write("시뮬레이터 출력을 해석하지 못했습니다. 원본:\n")
    sys.stderr.write(out + "\n")
    sys.exit(1)

nchk = int(m_n.group(1))
nfail = int(m_f.group(1))

# gdb 는 반복 값을 "1 <repeats 20 times>" 로 줄여 출력한다
vals = []
for tok in m_o.group(1).split(","):
    tok = tok.strip()
    rep = re.match(r"(\d+)\s*<repeats (\d+) times>", tok)
    if rep:
        vals.extend([int(rep.group(1))] * int(rep.group(2)))
    elif tok:
        vals.append(int(tok))

print("")
print("=== knockfp / classify 단위 테스트 (avr-gdb AVR 시뮬레이터 실행) ===")
print("")
for i in range(nchk):
    ok = i < len(vals) and vals[i] == 1
    name = names[i] if i < len(names) else "(이름 미상)"
    print("  %-4s %s" % ("PASS" if ok else "FAIL", name))

print("")
print("  검사 %d개 중 실패 %d개" % (nchk, nfail))
if len(names) != nchk:
    print("  주의: 소스의 check() 개수(%d)와 실행 수(%d)가 다릅니다."
          % (len(names), nchk))
sys.exit(1 if nfail else 0)
