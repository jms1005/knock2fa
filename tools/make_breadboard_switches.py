# -*- coding: utf-8 -*-
"""
make_breadboard_switches.py — 브링업 ②단계(스위치 4개) 전용 브레드보드도

figures/breadboard.svg 는 스위치+피에조+OLED 를 한 장에 다 그려서, 지금
스위치만 연결하는 사람에게는 화면이 복잡하다. 이 스크립트는 딱 지금
필요한 것만 — Uno 의 GND·D2~D5 다섯 핀과 스위치 4개 — 그린다.
피에조·OLED 는 아직 등장하지 않으므로 아예 그리지 않는다(전원 레일도
GND 쪽만 쓴다. +5V 는 이 단계에서 아무 데도 안 쓴다).

전기 규칙은 breadboard.svg 와 같다: 트렌치 위/아래는 다른 노드, 같은 열의
a~e(또는 f~j) 는 같은 노드, GND 쪽 열과 신호 쪽 열에 각각 점퍼 하나씩.

실행:  python tools/make_breadboard_switches.py
출력:  figures/breadboard_switches.svg
"""

import io
import os
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

W, H = 1180, 560
FONT = "'Malgun Gothic','맑은 고딕','Noto Sans KR',sans-serif"
INK = "#1e293b"
MUTE = "#64748b"
HOLE = "#cbd5e1"
RAIL_BLUE = "#2563eb"
WIRE_GND = "#1e293b"
WIRE_SIG = "#0369a1"

out = []


def add(s):
    out.append(s)


def wire(pts, color=INK, w=2.2):
    d = " ".join("%g,%g" % p for p in pts)
    add('<polyline points="%s" fill="none" stroke="%s" stroke-width="%g" '
        'stroke-linecap="round" stroke-linejoin="round"/>' % (d, color, w))


def line(x1, y1, x2, y2, w=2, color=INK):
    add('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="%g"/>'
        % (x1, y1, x2, y2, color, w))


def txt(x, y, s, size=12, anchor="start", weight="400", color=INK):
    add('<text x="%g" y="%g" font-size="%g" text-anchor="%s" font-weight="%s" '
        'fill="%s">%s</text>' % (x, y, size, anchor, weight, color, escape(s)))


def box(x, y, w, h, fill="#ffffff", stroke=INK, sw=2, rx=0):
    add('<rect x="%g" y="%g" width="%g" height="%g" rx="%g" fill="%s" '
        'stroke="%s" stroke-width="%g"/>' % (x, y, w, h, rx, fill, stroke, sw))


def hole(x, y):
    add('<circle cx="%g" cy="%g" r="3" fill="%s"/>' % (x, y, HOLE))


def dot(x, y, color=INK):
    add('<circle cx="%g" cy="%g" r="4" fill="%s"/>' % (x, y, color))


COLS = 20
COL_PITCH = 24
ROW_PITCH = 24
BB_X0 = 380
BB_Y0 = 100
RAIL_GAP = 18
TRENCH = 32


def x_of(c):
    return BB_X0 + c * COL_PITCH


Y_RAIL_MINUS = BB_Y0
Y_A = Y_RAIL_MINUS + ROW_PITCH + RAIL_GAP
ROWS_TOP = {r: Y_A + i * ROW_PITCH for i, r in enumerate("abcde")}
Y_F0 = ROWS_TOP["e"] + ROW_PITCH + TRENCH
ROWS_BOT = {r: Y_F0 + i * ROW_PITCH for i, r in enumerate("fghij")}

BB_X1 = x_of(COLS - 1)
BB_Y1 = ROWS_BOT["j"]

SW_COLS = [(1, 3), (6, 8), (11, 13), (16, 18)]   # (GND 열, 신호 열) x KEY1~4


def draw_board():
    box(BB_X0 - 34, BB_Y0 - 26, (BB_X1 - BB_X0) + 68, (BB_Y1 - BB_Y0) + 60,
        "#f8fafc", "#94a3b8", 1.6, 10)

    line(x_of(0) - 10, Y_RAIL_MINUS, x_of(COLS - 1) + 10, Y_RAIL_MINUS, 2.2, RAIL_BLUE)
    txt(x_of(0) - 24, Y_RAIL_MINUS + 4, "-", 13, "end", "700", RAIL_BLUE)
    txt(x_of(0) + 10, Y_RAIL_MINUS - 12, "GND 레일", 10.5, "start", "600", RAIL_BLUE)
    for c in range(COLS):
        if c % 5 == 4:
            continue
        hole(x_of(c), Y_RAIL_MINUS)

    for rows in (ROWS_TOP, ROWS_BOT):
        for r, y in rows.items():
            txt(x_of(0) - 16, y + 4, r, 10.5, "end", "400", MUTE)
            for c in range(COLS):
                hole(x_of(c), y)

    txt((BB_X0 + BB_X1) / 2.0, BB_Y1 + 26,
        "+5V 레일은 이 단계에서 쓰지 않는다 (피에조 클램프·OLED 는 다음 단계).",
        11, "middle", "400", MUTE)


def draw_switch(colA, colB, label):
    xa, xb = x_of(colA), x_of(colB)
    ye, yf = ROWS_TOP["e"], ROWS_BOT["f"]
    box(xa - 14, ye - 4, (xb - xa) + 28, (yf - ye) + 8, "#fef9c3", "#a16207", 1.6, 6)
    for cx, cy in ((xa, ye), (xb, ye), (xa, yf), (xb, yf)):
        dot(cx, cy, "#a16207")
    txt((xa + xb) / 2.0, ye - 10, label, 12, "middle", "700", "#713f12")


def draw_switches():
    for i, (gcol, scol) in enumerate(SW_COLS):
        draw_switch(gcol, scol, "SW%d (KEY%d)" % (i + 1, i + 1))
        wire([(x_of(gcol), ROWS_TOP["a"]), (x_of(gcol), Y_RAIL_MINUS)], WIRE_GND, 2)
        dot(x_of(gcol), ROWS_TOP["a"])
        dot(x_of(scol), ROWS_TOP["a"])


def draw_uno_and_stubs():
    ux0, uy0 = 40, BB_Y0 - 14
    uw = BB_X0 - ux0 - 60
    uh = (BB_Y1 - BB_Y0) + 26
    box(ux0, uy0, uw, uh, "#f8fafc")
    txt(ux0 + uw / 2.0, uy0 + 30, "Arduino Uno", 16, "middle", "700")
    txt(ux0 + uw / 2.0, uy0 + 52, "(ATmega328P 보드)", 12, "middle", "400", MUTE)

    pins = [
        ("GND", WIRE_GND, (x_of(0), Y_RAIL_MINUS)),
        ("D2", WIRE_SIG, (x_of(SW_COLS[0][1]), ROWS_TOP["a"])),
        ("D3", WIRE_SIG, (x_of(SW_COLS[1][1]), ROWS_TOP["a"])),
        ("D4", WIRE_SIG, (x_of(SW_COLS[2][1]), ROWS_TOP["a"])),
        ("D5", WIRE_SIG, (x_of(SW_COLS[3][1]), ROWS_TOP["a"])),
    ]
    n = len(pins)
    top, bot = uy0 + 90, uy0 + uh - 70
    for i, (label, color, (tx, ty)) in enumerate(pins):
        sy = top + i * ((bot - top) / float(n - 1))
        wire([(ux0 + uw, sy), (tx, sy), (tx, ty)], color, 2)
        dot(ux0 + uw, sy, color)
        txt(ux0 + uw - 10, sy - 6, label, 11, "end", "600", color)

    txt(ux0 + uw / 2.0, uy0 + uh - 20, "다른 핀(D7,A0,A4,A5,5V)은",
        10.5, "middle", "400", MUTE)
    txt(ux0 + uw / 2.0, uy0 + uh - 6, "다음 단계(피에조·OLED)에서 쓴다",
        10.5, "middle", "400", MUTE)


add('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
    'width="%d" height="%d" font-family="%s">' % (W, H, W, H, FONT))
add('<rect width="%d" height="%d" fill="#ffffff"/>' % (W, H))
box(14, 14, W - 28, H - 28, "none", INK, 2)
txt(W / 2.0, 40, "knock2fa 브링업 ② — 스위치 4개만 연결한 상태", 17,
    "middle", "700")
txt(W / 2.0, 60,
    "지금 이것만 꽂으면 된다. 피에조·OLED 는 다음 단계에서 추가한다.",
    12, "middle", "400", MUTE)

draw_board()
draw_switches()
draw_uno_and_stubs()

LX, LY = 40, H - 30
legend = [("GND", WIRE_GND), ("디지털 신호 (D2~D5)", WIRE_SIG)]
lx = LX
for name, c in legend:
    line(lx, LY, lx + 26, LY, 3, c)
    txt(lx + 32, LY + 4, name, 11.5, "start", "600", c)
    lx += 230

add('</svg>')

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
outdir = os.path.join(root, "figures")
if not os.path.isdir(outdir):
    os.makedirs(outdir)
path = os.path.join(outdir, "breadboard_switches.svg")
doc = "\n".join(out)
ET.fromstring(doc)
io.open(path, "w", encoding="utf-8").write(doc)
print("생성 완료: %s (%d bytes, XML 검증 통과)" % (path, os.path.getsize(path)))
