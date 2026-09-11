# -*- coding: utf-8 -*-
"""
make_breadboard.py — knock2fa 브레드보드 실배치도 생성기

figures/schematic.svg 가 전기적 연결을 기호(저항 기호, 다이오드 기호 등)로
보여준다면, 이 파일은 "실제로 어느 구멍에 꽂는지"를 브레드보드 격자 위에
그대로 배치해서 보여준다. 전기적으로는 schematic.svg 와 완전히 동일한 회로다.

브레드보드 전기 규칙 (이 스크립트가 따르는 것)
  - 중앙 홈(트렌치) 위/아래는 서로 다른 노드다. 같은 칸 번호라도 위 블록
    (a~e행)과 아래 블록(f~j행)은 연결되어 있지 않다.
  - 한 블록 안에서는 같은 열(칸)의 a~e(또는 f~j) 다섯 구멍이 전부 한 노드다.
    그래서 부품 여러 개를 "같은 노드"에 물릴 때는 같은 열의 다른 행 구멍을
    쓴다.
  - 위/아래 전원 레일은 서로 연결되어 있지 않으므로, 오른쪽 끝에서 점퍼선
    (레일 브리지)으로 한 번 이어준다.
  - 택트 스위치는 트렌치를 걸치도록 꽂는다. 같은 변(좌/우)의 두 다리는
    스위치 내부에서 항상 붙어 있고, 눌렀을 때만 좌변과 우변이 이어진다.
    그래서 한쪽 열은 GND, 반대쪽 열은 신호선(D2 등)으로 쓰면 눌렀을 때만
    신호선이 GND로 당겨지는 풀업 버튼이 된다.

실행:  python tools/make_breadboard.py
출력:  figures/breadboard.svg
"""

import io
import os
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

W, H = 1680, 700
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
WARN = "#b91c1c"

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


STAGE_C = "#0f766e"


def badge(x, y, num):
    """README §9 브링업 순서 번호 배지. 이 부품군을 몇 번째로 연결하는지 표시한다."""
    add('<circle cx="%g" cy="%g" r="15" fill="%s" stroke="#ffffff" stroke-width="2"/>'
        % (x, y, STAGE_C))
    txt(x, y + 5, str(num), 14, "middle", "700", "#ffffff")


# ---------------------------- 브레드보드 격자 ----------------------------

COLS = 40
COL_PITCH = 24
ROW_PITCH = 24
BB_X0 = 600
BB_Y0 = 108
RAIL_GAP = 18
TRENCH = 32


def x_of(c):
    return BB_X0 + c * COL_PITCH


Y_RAIL_T_PLUS = BB_Y0
Y_RAIL_T_MINUS = BB_Y0 + ROW_PITCH
Y_A = Y_RAIL_T_MINUS + ROW_PITCH + RAIL_GAP
ROWS_TOP = {r: Y_A + i * ROW_PITCH for i, r in enumerate("abcde")}
Y_F0 = ROWS_TOP["e"] + ROW_PITCH + TRENCH
ROWS_BOT = {r: Y_F0 + i * ROW_PITCH for i, r in enumerate("fghij")}
Y_RAIL_B_MINUS = ROWS_BOT["j"] + ROW_PITCH + RAIL_GAP
Y_RAIL_B_PLUS = Y_RAIL_B_MINUS + ROW_PITCH

BB_X1 = x_of(COLS - 1)
BB_Y1 = Y_RAIL_B_PLUS

# ---- 부품이 꽂히는 열 번호 (0-based) ----
SW_COLS = [(1, 3), (6, 8), (11, 13), (16, 18)]   # (GND 열, 신호 열) x KEY1~4
MCU_TAP_COL = 20     # PD7(AIN1) 과 PC0(ADC0) 이 함께 물리는 열
PZ_NODE_COL = 27     # R3 건너편 "피에조 노드" 열
OLED_COLS = (31, 32, 33, 34)   # VCC, GND, SDA, SCL


def draw_board():
    box(BB_X0 - 34, BB_Y0 - 30, (BB_X1 - BB_X0) + 34 + 140, (BB_Y1 - BB_Y0) + 60,
        "#f8fafc", "#94a3b8", 1.6, 10)

    for y, color, label in ((Y_RAIL_T_PLUS, RAIL_RED, "+"),
                            (Y_RAIL_T_MINUS, RAIL_BLUE, "-"),
                            (Y_RAIL_B_MINUS, RAIL_BLUE, "-"),
                            (Y_RAIL_B_PLUS, RAIL_RED, "+")):
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

    for c in range(0, COLS, 5):
        txt(x_of(c), Y_A - 8, str(c + 1), 9.5, "middle", "400", MUTE)

    txt((BB_X0 + BB_X1) / 2.0, BB_Y1 + 26,
        "같은 열(세로줄)의 a~e, f~j 다섯 구멍은 서로 연결된 한 노드다. "
        "트렌치(가운데 홈) 위아래는 연결되어 있지 않다.",
        11.5, "middle", "400", MUTE)


def draw_rail_bridges():
    xb1 = x_of(COLS - 1) + 30
    xb2 = xb1 + 16
    wire([(x_of(COLS - 1), Y_RAIL_T_PLUS), (xb1, Y_RAIL_T_PLUS),
          (xb1, Y_RAIL_B_PLUS), (x_of(COLS - 1), Y_RAIL_B_PLUS)], WIRE_VCC, 2.2)
    wire([(x_of(COLS - 1), Y_RAIL_T_MINUS), (xb2, Y_RAIL_T_MINUS),
          (xb2, Y_RAIL_B_MINUS), (x_of(COLS - 1), Y_RAIL_B_MINUS)], WIRE_GND, 2.2)
    txt(xb2 + 8, (Y_RAIL_T_PLUS + Y_RAIL_B_PLUS) / 2.0, "레일", 11, "start", "700", MUTE)
    txt(xb2 + 8, (Y_RAIL_T_PLUS + Y_RAIL_B_PLUS) / 2.0 + 16, "브리지", 11, "start", "700", MUTE)


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
        wire([(x_of(gcol), ROWS_TOP["a"]), (x_of(gcol), Y_RAIL_T_MINUS)], WIRE_GND, 2)
        dot(x_of(gcol), ROWS_TOP["a"])
        dot(x_of(scol), ROWS_TOP["a"])


def draw_piezo():
    dot(x_of(MCU_TAP_COL), ROWS_TOP["a"])
    dot(x_of(MCU_TAP_COL), ROWS_TOP["b"])
    txt(x_of(MCU_TAP_COL), ROWS_TOP["a"] - 10, "PD7/PC0 노드", 10.5, "middle", "700", WIRE_SIG)

    r3y = ROWS_TOP["c"]
    bw = (x_of(PZ_NODE_COL) - x_of(MCU_TAP_COL)) - 24
    box(x_of(MCU_TAP_COL) + 12, r3y - 9, bw, 18, "#ffffff", INK, 1.6, 3)
    line(x_of(MCU_TAP_COL), r3y, x_of(MCU_TAP_COL) + 12, r3y, 2, INK)
    line(x_of(PZ_NODE_COL) - 12, r3y, x_of(PZ_NODE_COL), r3y, 2, INK)
    dot(x_of(MCU_TAP_COL), r3y)
    dot(x_of(PZ_NODE_COL), r3y)
    txt((x_of(MCU_TAP_COL) + x_of(PZ_NODE_COL)) / 2.0, r3y - 14, "R3 1kΩ",
        11, "middle", "700")

    # R4(블리드)/D2(과전압 클램프)/D3(음의 스윙 클램프) 는 전부 피에조 노드
    # (PZ_NODE_COL) 에 다리 하나씩을 꽂지만, 라벨이 겹치지 않도록 레일까지
    # 가는 경로를 세 갈래(왼쪽/가운데/오른쪽)로 펼쳐서 그린다.
    dot(x_of(PZ_NODE_COL), ROWS_TOP["a"])
    wire([(x_of(PZ_NODE_COL), ROWS_TOP["a"]), (x_of(PZ_NODE_COL), Y_RAIL_T_MINUS)],
         WIRE_GND, 2.2)
    txt(x_of(PZ_NODE_COL) + 6, ROWS_TOP["a"] - 18,
        "R4 1MΩ", 10.5, "middle", "700", WARN)
    txt(x_of(PZ_NODE_COL) + 6, ROWS_TOP["a"] - 4,
        "(블리드, 필수!)", 9.5, "middle", "700", WARN)

    d2x = x_of(PZ_NODE_COL) - 56
    dot(x_of(PZ_NODE_COL), ROWS_TOP["b"])
    wire([(x_of(PZ_NODE_COL), ROWS_TOP["b"]), (d2x, ROWS_TOP["b"]),
          (d2x, Y_RAIL_T_PLUS)], WIRE_VCC, 2)
    txt(d2x, Y_RAIL_T_PLUS - 10, "D2", 10.5, "middle", "700", WIRE_VCC)
    txt(d2x, Y_RAIL_T_PLUS - 24, "1N4148", 9.5, "middle", "700", WIRE_VCC)

    d3x = x_of(PZ_NODE_COL) + 40
    dot(x_of(PZ_NODE_COL), ROWS_TOP["d"])
    wire([(x_of(PZ_NODE_COL), ROWS_TOP["d"]), (d3x, ROWS_TOP["d"]),
          (d3x, Y_RAIL_T_MINUS)], WIRE_GND, 2)
    txt(d3x, ROWS_TOP["d"] - 22, "D3", 10.5, "middle", "700", INK)
    txt(d3x, ROWS_TOP["d"] - 8, "1N4148", 9.5, "middle", "700", INK)

    dot(x_of(PZ_NODE_COL), ROWS_TOP["e"])
    bz_x, bz_y = x_of(PZ_NODE_COL) + 96, ROWS_TOP["e"]
    line(x_of(PZ_NODE_COL), ROWS_TOP["e"], bz_x - 18, bz_y, 2, INK)
    add('<circle cx="%g" cy="%g" r="18" fill="#e2e8f0" stroke="%s" stroke-width="1.6"/>'
        % (bz_x, bz_y, INK))
    txt(bz_x, bz_y + 5, "BZ1", 11, "middle", "700")
    txt(bz_x, bz_y + 32, "피에조", 10, "middle", "400", MUTE)
    wire([(bz_x, bz_y + 18), (bz_x, Y_RAIL_T_MINUS + 46), (x_of(PZ_NODE_COL) + 4,
          Y_RAIL_T_MINUS + 46), (x_of(PZ_NODE_COL) + 4, Y_RAIL_T_MINUS)], WIRE_GND, 2)


def draw_oled():
    ow, oh = 210, 52
    ox = x_of(OLED_COLS[0]) - 20
    oy = ROWS_BOT["g"] - oh + 20
    box(ox, oy, ow, oh, "#eef2ff", "#4338ca", 1.6, 6)
    txt(ox + ow / 2.0, oy + 21, "J2 — SSD1306 OLED", 11.5, "middle", "700", "#3730a3")
    txt(ox + ow / 2.0, oy + 39, "128x64, I2C 0x3C (모듈에 따라 0x3D)", 10, "middle",
        "400", MUTE)

    labels = ["VCC", "GND", "SDA", "SCL"]
    colors = [WIRE_VCC, WIRE_GND, WIRE_I2C, WIRE_I2C]
    for lab, col, c in zip(labels, colors, OLED_COLS):
        hx = x_of(c)
        dot(hx, ROWS_BOT["j"], col)
        line(hx, oy + oh, hx, ROWS_BOT["j"], 2, col)
        txt(hx, ROWS_BOT["j"] + 17, lab, 9.5, "middle", "600", col)

    wire([(x_of(OLED_COLS[0]), ROWS_BOT["j"]), (x_of(OLED_COLS[0]), Y_RAIL_B_PLUS)],
         WIRE_VCC, 2)
    wire([(x_of(OLED_COLS[1]), ROWS_BOT["j"]), (x_of(OLED_COLS[1]), Y_RAIL_B_MINUS)],
         WIRE_GND, 2)


def draw_uno_and_stubs():
    ux0, uy0 = 40, BB_Y0 - 18
    uw = BB_X0 - ux0 - 70
    uh = (BB_Y1 - BB_Y0) + 36
    box(ux0, uy0, uw, uh, "#f8fafc")
    txt(ux0 + uw / 2.0, uy0 + 30, "Arduino Uno", 16, "middle", "700")
    txt(ux0 + uw / 2.0, uy0 + 52, "(ATmega328P 보드)", 12, "middle", "400", MUTE)
    txt(ux0 + uw / 2.0, uy0 + uh - 16, "USB 케이블로 PC 연결 (전원 + UART 로그)",
        10.5, "middle", "400", MUTE)

    pins = [
        ("GND", WIRE_GND, (x_of(0), Y_RAIL_T_MINUS)),
        ("5V", WIRE_VCC, (x_of(0), Y_RAIL_T_PLUS)),
        ("D2", WIRE_SIG, (x_of(SW_COLS[0][1]), ROWS_TOP["a"])),
        ("D3", WIRE_SIG, (x_of(SW_COLS[1][1]), ROWS_TOP["a"])),
        ("D4", WIRE_SIG, (x_of(SW_COLS[2][1]), ROWS_TOP["a"])),
        ("D5", WIRE_SIG, (x_of(SW_COLS[3][1]), ROWS_TOP["a"])),
        ("D7 (AIN1)", WIRE_SIG, (x_of(MCU_TAP_COL), ROWS_TOP["a"])),
        ("A0 (ADC0)", WIRE_SIG, (x_of(MCU_TAP_COL), ROWS_TOP["b"])),
        ("A4 (SDA)", WIRE_I2C, (x_of(OLED_COLS[2]), ROWS_BOT["j"])),
        ("A5 (SCL)", WIRE_I2C, (x_of(OLED_COLS[3]), ROWS_BOT["j"])),
    ]
    n = len(pins)
    top, bot = uy0 + 74, uy0 + uh - 34
    for i, (label, color, (tx, ty)) in enumerate(pins):
        sy = top + i * ((bot - top) / float(n - 1))
        wire([(ux0 + uw, sy), (tx, sy), (tx, ty)], color, 2)
        dot(ux0 + uw, sy, color)
        txt(ux0 + uw - 10, sy - 6, label, 10.5, "end", "600", color)


# ---------------------------- 조립 ----------------------------

add('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
    'width="%d" height="%d" font-family="%s">' % (W, H, W, H, FONT))
add('<rect width="%d" height="%d" fill="#ffffff"/>' % (W, H))
box(14, 14, W - 28, H - 28, "none", INK, 2)
txt(W / 2.0, 40, "knock2fa — 브레드보드 실배치도 (스위치 4개 + 피에조 + OLED)",
    17, "middle", "700")
txt(W / 2.0, 60,
    "figures/schematic.svg 와 전기적으로 동일한 회로다. 어느 구멍에 꽂는지만 "
    "실제 배치로 보여준다. 원 번호 = README §9 브링업 순서 (① 보드만 → "
    "한 번에 다 연결하지 말 것).", 12, "middle", "400", MUTE)

draw_board()
draw_rail_bridges()
draw_switches()
draw_piezo()
draw_oled()
draw_uno_and_stubs()

# 브링업 순서 배지 (README §9). ①보드만 은 부품이 없어 배지가 없다.
badge(x_of(SW_COLS[0][0]) - 30, ROWS_TOP["e"] - 34, 2)
badge(x_of(MCU_TAP_COL) - 30, ROWS_TOP["a"] - 34, 4)
badge(x_of(OLED_COLS[0]) - 34, ROWS_BOT["g"] - 40, 3)

# 범례
LX, LY = 40, H - 34
legend = [("GND", WIRE_GND), ("+5V", WIRE_VCC), ("디지털 신호 (D2~D5, D7, A0)", WIRE_SIG),
          ("I2C (SDA/SCL)", WIRE_I2C)]
lx = LX
for name, c in legend:
    line(lx, LY, lx + 26, LY, 3, c)
    txt(lx + 32, LY + 4, name, 11.5, "start", "600", c)
    lx += 210

badge(lx + 14, LY, 2)
txt(lx + 36, LY + 4, "~④ = 브링업 순서 (README §9)", 11.5, "start", "600", STAGE_C)

add('</svg>')

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
outdir = os.path.join(root, "figures")
if not os.path.isdir(outdir):
    os.makedirs(outdir)
path = os.path.join(outdir, "breadboard.svg")
doc = "\n".join(out)
# 저장 전 XML 검증 (schematic.svg 와 같은 원칙)
ET.fromstring(doc)
io.open(path, "w", encoding="utf-8").write(doc)
print("생성 완료: %s (%d bytes, XML 검증 통과)" % (path, os.path.getsize(path)))
