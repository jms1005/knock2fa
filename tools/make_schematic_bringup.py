# -*- coding: utf-8 -*-
"""
make_schematic_bringup.py — 회로도(schematic.svg)에 브링업 순서 배지를 얹은
별도 사본 생성기.

제출용 나_회로도.pdf 의 원본인 schematic.svg 는 건드리지 않는다(심사용
문서라 표제란·문구를 임의로 바꾸면 안 된다). 대신 make_schematic.py 를
다시 실행해 최신 schematic.svg 를 만든 뒤, 그 내용을 그대로 복사해 "이 기호가
브링업 몇 번째 단계에 해당하는지" 배지(②③④)만 얹어 별도 파일로 저장한다.
①(보드만)·⑤(등록→인증)·⑥(액추에이터)는 부품 기호가 새로 추가되지 않으므로
배지가 없다 — 순서 전체 설명은 figures/bringup.svg 를 본다.

실행:  python tools/make_schematic_bringup.py
출력:  figures/schematic_bringup.svg
"""

import io
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

STAGE_C = "#0f766e"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGDIR = os.path.join(ROOT, "figures")
SRC = os.path.join(FIGDIR, "schematic.svg")
DST = os.path.join(FIGDIR, "schematic_bringup.svg")

# schematic.svg 안의 좌표계를 그대로 쓴다 (make_schematic.py 참고).
#   ② 스위치군: SW1(PD2) 인입 지점 근처
#   ③ OLED(J2) 모듈 박스 위
#   ④ 피에조 회로(R3 주변) 위
BADGES = [
    (2, 862, 380),
    (4, 1080, 194),
    (3, 1170, 732),
]


def badge_svg(num, x, y):
    return (
        '<circle cx="%g" cy="%g" r="16" fill="%s" stroke="#ffffff" '
        'stroke-width="2.4"/>'
        '<text x="%g" y="%g" font-size="15" text-anchor="middle" '
        'font-weight="700" fill="#ffffff">%d</text>'
    ) % (x, y, STAGE_C, x, y + 5, num)


def main():
    # 최신 상태로 다시 만든다 (schematic.py 를 고쳤는데 여기만 예전 그림을
    # 쓰는 사고를 막는다).
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "make_schematic.py")],
                    check=True)

    doc = io.open(SRC, encoding="utf-8").read()
    if "</svg>" not in doc:
        raise SystemExit("schematic.svg 형식이 예상과 다르다 (</svg> 없음)")

    caption = (
        '<text x="40" y="50" font-size="13" font-weight="700" fill="%s">'
        '브링업 순서 배지 (README §9): '
        '&#9312; 보드만 -&gt; &#9313; 스위치 -&gt; &#9314; OLED -&gt; '
        '&#9315; 피에조 -&gt; &#9316; 등록/인증 -&gt; &#9317; 액추에이터'
        '</text>'
    ) % STAGE_C

    inserts = "".join(badge_svg(n, x, y) for n, x, y in BADGES)
    doc = doc.replace("</svg>", caption + inserts + "</svg>")

    ET.fromstring(doc)
    io.open(DST, "w", encoding="utf-8").write(doc)
    print("생성 완료: %s (%d bytes, XML 검증 통과)" % (DST, os.path.getsize(DST)))


if __name__ == "__main__":
    main()
