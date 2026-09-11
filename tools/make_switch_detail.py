# -*- coding: utf-8 -*-
"""
make_switch_detail.py — 택트 스위치 1개의 GND/신호 연결 확대도

figures/breadboard.svg 의 SW1~SW4 부분이 너무 작아 손으로 따라 꽂기
어렵다는 요청으로 추가했다. 스위치 1개(SW1 예시)만 크게 확대해서,
"안 눌렀을 때"와 "눌렀을 때" 두 상태를 나란히 보여준다.

의도적으로 스위치 내부의 정확한 다리 결선(어느 두 다리가 원래부터
붙어있는지)은 그리지 않는다. 제품마다 조금씩 달라 자신 없는 사실을
단정하는 대신, 실제로 검증 가능한 사실만 그린다.
  - 스위치는 트렌치(가운데 홈)를 걸치도록 꽂는다.
  - GND 점퍼는 한쪽 열에, 신호선(D2 등)은 반대쪽 열에 꽂는다.
  - 안 눌렀을 때는 두 열이 끊겨 있고(D2 = HIGH), 누르면 이어진다(D2 = LOW).
  - 반대로 나오면(눌러야 HIGH) 스위치를 90도 돌려 다시 꽂아보라고 안내한다.

실행:  python tools/make_switch_detail.py
출력:  figures/switch_detail.svg
"""

import io
import os
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

W, H = 1400, 640
FONT = "'Malgun Gothic','맑은 고딕','Noto Sans KR',sans-serif"
INK = "#1e293b"
MUTE = "#64748b"
HOLE = "#cbd5e1"
RAIL_BLUE = "#2563eb"
WIRE_GND = "#1e293b"
WIRE_SIG = "#0369a1"
OPEN_C = "#94a3b8"
CONN_C = "#16a34a"
WARN = "#b91c1c"

out = []


def add(s):
    out.append(s)


def wire(pts, color=INK, w=2.4):
    d = " ".join("%g,%g" % p for p in pts)
    add('<polyline points="%s" fill="none" stroke="%s" stroke-width="%g" '
        'stroke-linecap="round" stroke-linejoin="round"/>' % (d, color, w))


def dashed(x1, y1, x2, y2, color, w=3, dash="6,6"):
    add('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="%g" '
        'stroke-dasharray="%s" stroke-linecap="round"/>' % (x1, y1, x2, y2, color, w, dash))


def line(x1, y1, x2, y2, w=2, color=INK):
    add('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="%g"/>'
        % (x1, y1, x2, y2, color, w))


def txt(x, y, s, size=12, anchor="start", weight="400", color=INK):
    add('<text x="%g" y="%g" font-size="%g" text-anchor="%s" font-weight="%s" '
        'fill="%s">%s</text>' % (x, y, size, anchor, weight, color, escape(s)))


def box(x, y, w, h, fill="#ffffff", stroke=INK, sw=2, rx=0):
    add('<rect x="%g" y="%g" width="%g" height="%g" rx="%g" fill="%s" '
        'stroke="%s" stroke-width="%g"/>' % (x, y, w, h, rx, fill, stroke, sw))


def hole(x, y, r=4.2):
    add('<circle cx="%g" cy="%g" r="%g" fill="%s"/>' % (x, y, r, HOLE))


def dot(x, y, r=5.4, color=INK):
    add('<circle cx="%g" cy="%g" r="%g" fill="%s"/>' % (x, y, r, color))


def draw_panel(px0, pressed, title):
    pw = 600
    colA = px0 + 150   # GND 쪽 열
    colB = px0 + 380   # 신호(D2) 쪽 열

    rail_y = 150
    row_a_y = 224
    dots_y = 260
    row_e_y = 330
    trench_y0, trench_y1 = row_e_y + 14, row_e_y + 58
    row_f_y = trench_y1 + 14

    box(px0, 96, pw, 470, "#f8fafc", "#94a3b8", 1.6, 10)
    txt(px0 + pw / 2.0, 130, title, 16, "middle", "700",
        CONN_C if pressed else MUTE)

    # GND 레일
    line(colA - 70, rail_y, colB + 70, rail_y, 2.2, RAIL_BLUE)
    txt(colA - 86, rail_y + 4, "-", 14, "end", "700", RAIL_BLUE)
    txt(colA - 60, rail_y - 12, "GND 레일", 10.5, "start", "600", RAIL_BLUE)
    for cx in (colA - 40, colA, colB, colB + 40):
        hole(cx, rail_y)

    # 단자열 a행 (GND 점퍼 / 신호선이 실제로 꽂히는 자리)
    hole(colA, row_a_y)
    hole(colB, row_a_y)
    txt(colA - 14, row_a_y - 30, "GND 점퍼", 10, "end", "600", WIRE_GND)
    txt(colA - 14, row_a_y - 16, "꽂는 구멍", 10, "end", "600", WIRE_GND)
    txt(colB + 14, row_a_y - 30, "D2 점퍼", 10, "start", "600", WIRE_SIG)
    txt(colB + 14, row_a_y - 16, "꽂는 구멍", 10, "start", "600", WIRE_SIG)

    # a행 -> e행: 같은 열이라 이미 연결된 구간 (점선 표시)
    dashed(colA, row_a_y + 8, colA, row_e_y - 8, MUTE, 2, "3,4")
    dashed(colB, row_a_y + 8, colB, row_e_y - 8, MUTE, 2, "3,4")
    txt(colA - 92, dots_y + 4, "같은 열이라", 9.5, "start", "400", MUTE)
    txt(colA - 92, dots_y + 18, "이미 연결됨", 9.5, "start", "400", MUTE)

    # 트렌치
    box(colA - 90, trench_y0, (colB + 90) - (colA - 90), trench_y1 - trench_y0,
        "#e2e8f0", "none", 0, 4)
    txt((colA + colB) / 2.0, (trench_y0 + trench_y1) / 2.0 + 4, "트렌치 (가운데 홈)",
        10.5, "middle", "600", "#475569")

    # 스위치 몸체 + 버튼
    body_fill = "#dcfce7" if pressed else "#fef9c3"
    body_stroke = CONN_C if pressed else "#a16207"
    box(colA - 30, row_e_y - 18, (colB - colA) + 60, (row_f_y - row_e_y) + 36,
        body_fill, body_stroke, 2, 8)
    midy = (row_e_y + row_f_y) / 2.0
    r = 22 if pressed else 26
    add('<circle cx="%g" cy="%g" r="%g" fill="#ffffff" stroke="%s" stroke-width="2.4"/>'
        % ((colA + colB) / 2.0, midy, r, body_stroke))
    cx0 = (colA + colB) / 2.0
    if pressed:
        # 체크 표시
        wire([(cx0 - 9, midy), (cx0 - 2, midy + 8), (cx0 + 11, midy - 9)], CONN_C, 3.4)
    else:
        # X 표시
        line(cx0 - 8, midy - 8, cx0 + 8, midy + 8, 3, OPEN_C)
        line(cx0 - 8, midy + 8, cx0 + 8, midy - 8, 3, OPEN_C)

    # 4개 다리
    for cx, cy in ((colA, row_e_y), (colB, row_e_y), (colA, row_f_y), (colB, row_f_y)):
        dot(cx, cy, 5.4, body_stroke)

    # 몸체 밑, 결과 박스 위: 상태 한 줄 캡션
    cap_c = CONN_C if pressed else OPEN_C
    cap_t = "GND ↔ D2 연결됨" if pressed else "GND ↔ D2 끊김"
    txt(cx0, row_f_y + 30, cap_t, 10.5, "middle", "700", cap_c)

    # 실제 점퍼선
    wire([(colA, row_a_y), (colA, rail_y)], WIRE_GND, 2.6)
    wire([(colB, row_a_y), (colB, row_a_y - 46), (colB + 90, row_a_y - 46)], WIRE_SIG, 2.6)
    txt(colB + 96, row_a_y - 42, "→ Uno D2", 12, "start", "700", WIRE_SIG)

    # 결과
    res_c = CONN_C if pressed else WIRE_SIG
    res_t = "D2 = LOW  (눌림 감지됨)" if pressed else "D2 = HIGH  (내부 풀업)"
    box(colA - 30, row_f_y + 42, (colB - colA) + 60, 34, "#ffffff", res_c, 1.8, 6)
    txt((colA + colB) / 2.0, row_f_y + 64, res_t, 13, "middle", "700", res_c)


add('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
    'width="%d" height="%d" font-family="%s">' % (W, H, W, H, FONT))
add('<rect width="%d" height="%d" fill="#ffffff"/>' % (W, H))
box(14, 14, W - 28, H - 28, "none", INK, 2)
txt(W / 2.0, 42, "스위치 GND 연결 확대도 — SW1 (KEY1) 예시", 18, "middle", "700")
txt(W / 2.0, 64,
    "SW2~SW4 도 열 번호만 다를 뿐 방식은 완전히 같다 (GND 쪽 신호 쪽 두 열에 "
    "각각 점퍼 하나씩).", 12, "middle", "400", MUTE)

draw_panel(60, False, "① 평소 — 안 누름")
draw_panel(720, True, "② 누르는 순간")

# 하단 안내
NOTE_Y = 588
txt(60, NOTE_Y, "확인 방법: 아무것도 안 눌렀을 때 이미 반응이 있다면 —",
    12.5, "start", "700", WARN)
txt(60, NOTE_Y + 20,
    "배선이 틀린 게 아니라 스위치를 90도 돌려 꽂아야 하는 경우가 많다. "
    "돌려서 다시 꽂고 그대로 테스트해 보면 된다.", 12, "start", "400", INK)

add('</svg>')

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
outdir = os.path.join(root, "figures")
if not os.path.isdir(outdir):
    os.makedirs(outdir)
path = os.path.join(outdir, "switch_detail.svg")
doc = "\n".join(out)
ET.fromstring(doc)
io.open(path, "w", encoding="utf-8").write(doc)
print("생성 완료: %s (%d bytes, XML 검증 통과)" % (path, os.path.getsize(path)))
