# -*- coding: utf-8 -*-
"""
make_breadboard_oled.py — 브링업 ③단계(OLED) 전용 브레드보드도

②단계(스위치)는 이미 꽂혀 있다고 보고 그대로 두고, OLED(J2)만 새로 추가한
상태를 그린다. 피에조(④단계)는 아직 없으므로 그리지 않는다.

전기 규칙은 breadboard.svg 와 같다: 트렌치 위/아래는 다른 노드, 같은 열의
a~e(또는 f~j) 는 같은 노드. OLED 는 상단 블록(a~e) 에만 꽂으므로 하단
레일·레일 브리지가 필요 없다 — 회로가 전부 위쪽 레일 하나로 끝난다.

실행:  python tools/make_breadboard_oled.py
출력:  figures/breadboard_oled.svg
"""

import io
import os
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

W, H = 1400, 620
FONT = "'Malgun Gothic','맑은 고딕','Noto Sans KR',sans-serif"
INK = "#1e293b"
MUTE = "#64748b"
HOLE = "#cbd5e1"
RAIL_RED = "#dc2626"
RAIL_BLUE = "#2563eb"
WIRE_GND = "#1e293b"
WIRE_VCC = "#dc2626"
WIRE_SIG = "#0369a1"
WIRE_I2C = "#7c3aed"

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


COLS = 26
COL_PITCH = 24
ROW_PITCH = 24
BB_X0 = 380
BB_Y0 = 108
RAIL_GAP = 18
TRENCH = 32


def x_of(c):
    return BB_X0 + c * COL_PITCH


Y_RAIL_PLUS = BB_Y0
Y_RAIL_MINUS = BB_Y0 + ROW_PITCH
Y_A = Y_RAIL_MINUS + ROW_PITCH + RAIL_GAP
ROWS_TOP = {r: Y_A + i * ROW_PITCH for i, r in enumerate("abcde")}
Y_F0 = ROWS_TOP["e"] + ROW_PITCH + TRENCH
ROWS_BOT = {r: Y_F0 + i * ROW_PITCH for i, r in enumerate("fghij")}

BB_X1 = x_of(COLS - 1)
BB_Y1 = ROWS_BOT["j"]

SW_COLS = [(1, 3), (6, 8), (11, 13), (16, 18)]   # (GND 열, 신호 열) x KEY1~4
# 실제 모듈 실크스크린 순서: GND, VDD, SCK, SDA (왼쪽부터). 모듈마다 인쇄된
# 순서와 이름(VDD vs VCC, SCK vs SCL)이 다를 수 있으니 실물 라벨을 따른다.
OLED_COLS = (21, 22, 23, 24)                     # GND, VDD, SCK, SDA


def draw_board():
    box(BB_X0 - 34, BB_Y0 - 26, (BB_X1 - BB_X0) + 68, (BB_Y1 - BB_Y0) + 60,
        "#f8fafc", "#94a3b8", 1.6, 10)

    for y, color, label in ((Y_RAIL_PLUS, RAIL_RED, "+"),
                            (Y_RAIL_MINUS, RAIL_BLUE, "-")):
        line(x_of(0) - 10, y, x_of(COLS - 1) + 10, y, 2.2, color)
        txt(x_of(0) - 24, y + 4, label, 13, "end", "700", color)
        for c in range(COLS):
            if c % 5 == 4:
                continue
            hole(x_of(c), y)

    for rows in (ROWS_TOP, ROWS_BOT):
        for r, y in rows.items():
            txt(x_of(0) - 16, y + 4, r, 10.5, "end", "400", MUTE)
            for c in range(COLS):
                hole(x_of(c), y)

    txt((BB_X0 + BB_X1) / 2.0, BB_Y1 + 26,
        "아래쪽 레일은 이 단계에서 쓰지 않는다 (피에조는 다음 단계).",
        11, "middle", "400", MUTE)


def draw_switch(colA, colB, label):
    xa, xb = x_of(colA), x_of(colB)
    ye, yf = ROWS_TOP["e"], ROWS_BOT["f"]
    box(xa - 14, ye - 4, (xb - xa) + 28, (yf - ye) + 8, "#fef9c3", "#a16207", 1.6, 6)
    for cx, cy in ((xa, ye), (xb, ye), (xa, yf), (xb, yf)):
        dot(cx, cy, "#a16207")
    txt((xa + xb) / 2.0, ye - 10, label, 11.5, "middle", "700", "#713f12")


def draw_switches():
    """②단계에서 이미 꽂혀 있는 스위치. 흐리지 않고 그대로 보여준다."""
    for i, (gcol, scol) in enumerate(SW_COLS):
        draw_switch(gcol, scol, "SW%d" % (i + 1))
        wire([(x_of(gcol), ROWS_TOP["a"]), (x_of(gcol), Y_RAIL_MINUS)], WIRE_GND, 2)
        dot(x_of(gcol), ROWS_TOP["a"])
        dot(x_of(scol), ROWS_TOP["a"])


def draw_oled():
    """
    GND/VDD 는 레일이 위(row a 쪽)에 있으므로 박스 윗변에서 row a 로 뽑는다.
    SCK/SDA 는 Uno 가 아래쪽에서 들어오므로 박스 아랫변에서 row e 로 뽑는다.
    이렇게 위/아래로 나눠야 Uno 로 가는 긴 배선이 박스 몸통을 뚫고 지나가지
    않는다(둘 다 row a 로 모으면 아래에서 올라오는 선이 박스를 관통한다).

    실물 모듈 핀 순서 GND, VDD, SCK, SDA (왼쪽부터) 를 그대로 따른다 —
    SSD1306 모듈은 VCC 대신 VDD, SCL 대신 SCK 로 인쇄된 제품이 흔하다.
    신호 자체는 같다(VDD=VCC, SCK=SCL=A5).
    """
    gnd_c, vdd_c, sck_c, sda_c = OLED_COLS
    ow = x_of(OLED_COLS[-1]) - x_of(OLED_COLS[0]) + 56
    ox = x_of(OLED_COLS[0]) - 28
    oy = ROWS_TOP["b"] - 6
    oh = ROWS_TOP["d"] - ROWS_TOP["b"] + 12

    box(ox, oy, ow, oh, "#eef2ff", "#4338ca", 1.8, 8)
    txt(ox + ow / 2.0, oy + 22, "J2 — SSD1306 OLED", 12.5, "middle", "700", "#3730a3")
    txt(ox + ow / 2.0, oy + 40, "128x64, I2C 0x3C (모듈에 따라 0x3D)", 10.5,
        "middle", "400", MUTE)

    for lab, col, c in (("GND", WIRE_GND, gnd_c), ("VDD", WIRE_VCC, vdd_c)):
        hx = x_of(c)
        dot(hx, ROWS_TOP["a"], col)
        line(hx, oy, hx, ROWS_TOP["a"], 2, col)
        txt(hx, ROWS_TOP["a"] - 10, lab, 10, "middle", "700", col)

    for lab, col, c in (("SCK", WIRE_I2C, sck_c), ("SDA", WIRE_I2C, sda_c)):
        hx = x_of(c)
        dot(hx, ROWS_TOP["e"], col)
        line(hx, oy + oh, hx, ROWS_TOP["e"], 2, col)
        txt(hx, ROWS_TOP["e"] + 16, lab, 10, "middle", "700", col)

    wire([(x_of(vdd_c), ROWS_TOP["a"]), (x_of(vdd_c), Y_RAIL_PLUS)], WIRE_VCC, 2.2)
    wire([(x_of(gnd_c), ROWS_TOP["a"]), (x_of(gnd_c), Y_RAIL_MINUS)], WIRE_GND, 2.2)


def draw_uno_and_stubs():
    ux0, uy0 = 40, BB_Y0 - 22
    uw = BB_X0 - ux0 - 60
    uh = (BB_Y1 - BB_Y0) + 56
    box(ux0, uy0, uw, uh, "#f8fafc")
    txt(ux0 + uw / 2.0, uy0 + 30, "Arduino Uno", 16, "middle", "700")
    txt(ux0 + uw / 2.0, uy0 + 52, "(ATmega328P 보드)", 12, "middle", "400", MUTE)

    pins = [
        ("GND", WIRE_GND, (x_of(0), Y_RAIL_MINUS)),
        ("5V", WIRE_VCC, (x_of(0), Y_RAIL_PLUS)),
        ("D2", WIRE_SIG, (x_of(SW_COLS[0][1]), ROWS_TOP["a"])),
        ("D3", WIRE_SIG, (x_of(SW_COLS[1][1]), ROWS_TOP["a"])),
        ("D4", WIRE_SIG, (x_of(SW_COLS[2][1]), ROWS_TOP["a"])),
        ("D5", WIRE_SIG, (x_of(SW_COLS[3][1]), ROWS_TOP["a"])),
        ("A5 (SCK)", WIRE_I2C, (x_of(OLED_COLS[2]), ROWS_TOP["e"])),
        ("A4 (SDA)", WIRE_I2C, (x_of(OLED_COLS[3]), ROWS_TOP["e"])),
    ]
    n = len(pins)
    top, bot = uy0 + 90, uy0 + uh - 60
    for i, (label, color, (tx, ty)) in enumerate(pins):
        sy = top + i * ((bot - top) / float(n - 1))
        wire([(ux0 + uw, sy), (tx, sy), (tx, ty)], color, 2)
        dot(ux0 + uw, sy, color)
        txt(ux0 + uw - 10, sy - 6, label, 10.5, "end", "600", color)

    txt(ux0 + uw / 2.0, uy0 + uh - 16,
        "D7·A0(피에조)은 다음 단계에서 쓴다", 10.5, "middle", "400", MUTE)


add('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
    'width="%d" height="%d" font-family="%s">' % (W, H, W, H, FONT))
add('<rect width="%d" height="%d" fill="#ffffff"/>' % (W, H))
box(14, 14, W - 28, H - 28, "none", INK, 2)
txt(W / 2.0, 40, "knock2fa 브링업 ③ — 스위치 4개 + OLED", 17, "middle", "700")
txt(W / 2.0, 60,
    "②단계 스위치는 그대로 두고 OLED(J2)만 추가한다. 피에조는 다음 단계.",
    12, "middle", "400", MUTE)

draw_board()
draw_switches()
draw_oled()
draw_uno_and_stubs()

LX, LY = 40, H - 30
legend = [("GND", WIRE_GND), ("+5V", WIRE_VCC), ("디지털 신호 (D2~D5)", WIRE_SIG),
          ("I2C (SCK/SDA)", WIRE_I2C)]
lx = LX
for name, c in legend:
    line(lx, LY, lx + 26, LY, 3, c)
    txt(lx + 32, LY + 4, name, 11.5, "start", "600", c)
    lx += 220

add('</svg>')

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
outdir = os.path.join(root, "figures")
if not os.path.isdir(outdir):
    os.makedirs(outdir)
path = os.path.join(outdir, "breadboard_oled.svg")
doc = "\n".join(out)
ET.fromstring(doc)
io.open(path, "w", encoding="utf-8").write(doc)
print("생성 완료: %s (%d bytes, XML 검증 통과)" % (path, os.path.getsize(path)))
