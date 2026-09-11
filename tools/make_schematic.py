# -*- coding: utf-8 -*-
"""
make_schematic.py — knock2fa 회로도 SVG 생성기

제출물 「나. 회로도 (PDF 파일)」용 도면을 만든다.
좌표를 손으로 쓰면 실수가 잦으므로 부품 기호를 함수로 정의해 조립한다.
기존 PEDD 프로젝트의 도면 생성기와 같은 기호 규약을 쓴다.

실행:  python tools/make_schematic.py
출력:  figures/schematic.svg
"""

import io
import os
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

W, H = 1560, 1240
FONT = "'Malgun Gothic','맑은 고딕','Noto Sans KR',sans-serif"
INK = "#1e293b"
MUTE = "#64748b"
WARN = "#b91c1c"
ACCENT = "#7c3aed"

out = []


def add(s):
    out.append(s)


def wire(*pts, **kw):
    """직선 배선. pts는 (x, y) 튜플 나열."""
    color = kw.get("color", INK)
    w = kw.get("w", 2)
    d = " ".join("%g,%g" % p for p in pts)
    add('<polyline points="%s" fill="none" stroke="%s" stroke-width="%g" '
        'stroke-linecap="round" stroke-linejoin="round"/>' % (d, color, w))


def line(x1, y1, x2, y2, w=2.4, color=INK):
    add('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="%g"/>'
        % (x1, y1, x2, y2, color, w))


def dot(x, y):
    """접속점(정션). 단순 교차와 구분하기 위해 반드시 찍는다."""
    add('<circle cx="%g" cy="%g" r="4.5" fill="%s"/>' % (x, y, INK))


def txt(x, y, s, size=13, anchor="start", weight="400", color=INK):
    # 본문에 <, >, & 가 섞이면 SVG(XML)가 통째로 깨진다. 반드시 이스케이프.
    add('<text x="%g" y="%g" font-size="%g" text-anchor="%s" font-weight="%s" '
        'fill="%s">%s</text>'
        % (x, y, size, anchor, weight, color, escape(s)))


def box(x, y, w, h, fill="#ffffff", stroke=INK, sw=2, rx=0):
    add('<rect x="%g" y="%g" width="%g" height="%g" rx="%g" fill="%s" '
        'stroke="%s" stroke-width="%g"/>' % (x, y, w, h, rx, fill, stroke, sw))


# ---------------------------- 부품 기호 ----------------------------

def resistor_h(xc, y, ref, val):
    """가로 저항 (IEC 60617 직사각형 기호). 반환: 좌우 단자 x."""
    bw, bh = 74, 26
    box(xc - bw / 2.0, y - bh / 2.0, bw, bh)
    txt(xc, y - bh / 2.0 - 10, ref, 13, "middle", "700")
    txt(xc, y + bh / 2.0 + 19, val, 12.5, "middle")
    return xc - bw / 2.0, xc + bw / 2.0


def resistor_v(x, yc, ref, val, side="right"):
    """세로 저항. 반환: 상하 단자 y."""
    bw, bh = 26, 60
    box(x - bw / 2.0, yc - bh / 2.0, bw, bh)
    tx = x + bw / 2.0 + 9 if side == "right" else x - bw / 2.0 - 9
    an = "start" if side == "right" else "end"
    txt(tx, yc - 2, ref, 13, an, "700")
    txt(tx, yc + 15, val, 12.5, an)
    return yc - bh / 2.0, yc + bh / 2.0


def cap_v(x, yc, ref, val, side="right"):
    """세로 커패시터. 극판 2장. 반환: 상하 단자 y."""
    pw, gap = 34, 11
    line(x - pw / 2.0, yc - gap / 2.0, x + pw / 2.0, yc - gap / 2.0, 2.6)
    line(x - pw / 2.0, yc + gap / 2.0, x + pw / 2.0, yc + gap / 2.0, 2.6)
    tx = x + pw / 2.0 + 8 if side == "right" else x - pw / 2.0 - 8
    an = "start" if side == "right" else "end"
    txt(tx, yc - 2, ref, 13, an, "700")
    txt(tx, yc + 15, val, 12.5, an)
    return yc - gap / 2.0, yc + gap / 2.0


def crystal_v(x, yc, ref, val):
    """세로 수정 진동자. 반환: 상하 단자 y."""
    pw = 34
    line(x - pw / 2.0, yc - 12, x + pw / 2.0, yc - 12, 2.6)
    line(x - pw / 2.0, yc + 12, x + pw / 2.0, yc + 12, 2.6)
    box(x - 13, yc - 8, 26, 16)
    txt(x - pw / 2.0 - 8, yc - 2, ref, 13, "end", "700")
    txt(x - pw / 2.0 - 8, yc + 15, val, 12.5, "end")
    return yc - 12, yc + 12


def diode_v(x, yc, ref, val, side="right"):
    """세로 다이오드. 애노드 아래 / 캐소드 위 = 전류가 위로 흐른다.
    반환: 상하 단자 y."""
    hh, hw = 15, 15
    add('<path d="M %g %g L %g %g L %g %g Z" fill="none" stroke="%s" '
        'stroke-width="2.2"/>' % (x - hw, yc + hh, x + hw, yc + hh,
                                  x, yc - hh, INK))
    line(x - hw, yc - hh, x + hw, yc - hh, 2.8)   # 캐소드 바
    tx = x + hw + 9 if side == "right" else x - hw - 9
    an = "start" if side == "right" else "end"
    txt(tx, yc - 2, ref, 13, an, "700")
    txt(tx, yc + 15, val, 12.5, an)
    return yc - hh, yc + hh


def led_h(xa, y, ref, val):
    """가로 LED. 애노드 왼쪽 / 캐소드 오른쪽. 반환: 좌우 단자 x."""
    L, hh = 46, 17
    xb = xa + L
    add('<path d="M %g %g L %g %g L %g %g Z" fill="none" stroke="%s" '
        'stroke-width="2.2"/>' % (xa, y - hh, xa, y + hh, xb, y, INK))
    line(xb, y - hh, xb, y + hh, 2.8)
    cx = xa + L / 2.0
    for k in (0, 1):
        ox = cx - 9 + k * 16
        add('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" '
            'stroke-width="1.8" marker-end="url(#tip)"/>'
            % (ox, y - hh - 4, ox + 13, y - hh - 18, INK))
    txt(cx, y + hh + 21, ref, 13, "middle", "700")
    txt(cx, y + hh + 38, val, 12.5, "middle")
    return xa, xb


def switch_h(xa, y, ref):
    """가로 택트 스위치 (a접점). 반환: 좌우 단자 x."""
    L = 56
    xb = xa + L
    add('<circle cx="%g" cy="%g" r="4" fill="none" stroke="%s" '
        'stroke-width="2"/>' % (xa + 4, y, INK))
    add('<circle cx="%g" cy="%g" r="4" fill="none" stroke="%s" '
        'stroke-width="2"/>' % (xb - 4, y, INK))
    wire((xa + 8, y), (xb - 6, y - 18))
    txt(xb + 14, y + 5, ref, 13, "start", "700")
    return xa, xb


def piezo_v(x, yc, ref, val):
    """세로 압전(피에조) 디스크.
    세라믹 층을 두 전극이 감싼 형태로 그린다. 반환: 상하 단자 y."""
    hw, hh = 27, 13
    line(x - hw, yc - hh, x + hw, yc - hh, 3.2)      # 상부 전극
    line(x - hw, yc + hh, x + hw, yc + hh, 3.2)      # 하부 전극
    box(x - hw + 5, yc - hh + 3, (hw - 5) * 2, (hh - 3) * 2,
        "#e2e8f0", INK, 1.4)                          # 세라믹
    txt(x + hw + 10, yc - 2, ref, 13, "start", "700")
    txt(x + hw + 10, yc + 15, val, 12.5, "start")
    return yc - hh, yc + hh


def gnd(x, y):
    """접지 기호. 스터브 + 폭이 줄어드는 가로선 3개."""
    wire((x, y), (x, y + 12))
    for i, w2 in enumerate((18, 11, 5)):
        yy = y + 12 + i * 6
        line(x - w2, yy, x + w2, yy, 2.4)


def vcc(x, y):
    """전원 기호."""
    wire((x, y), (x, y - 18))
    line(x - 16, y - 18, x + 16, y - 18, 2.4)
    txt(x, y - 26, "+5V", 13, "middle", "700")


def connector(x, y, w, h, ref, name, pins):
    """커넥터/모듈 블록. pins = [(라벨, y), ...] 왼쪽 가장자리 단자."""
    box(x, y, w, h, "#f8fafc")
    txt(x + w / 2.0, y + 24, ref, 14, "middle", "700")
    txt(x + w / 2.0, y + 44, name, 12, "middle", "400", MUTE)
    for label, py in pins:
        txt(x + 12, py + 5, label, 12.5, "start", "600")


# ---------------------------- 도면 조립 ----------------------------

add('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
    'width="%d" height="%d" font-family="%s">' % (W, H, W, H, FONT))
add('<defs><marker id="tip" viewBox="0 0 10 10" refX="9" refY="5" '
    'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
    '<path d="M 0 0 L 10 5 L 0 10 z" fill="%s"/></marker></defs>' % INK)
add('<rect width="%d" height="%d" fill="#ffffff"/>' % (W, H))
box(14, 14, W - 28, H - 28, "none", INK, 2)

# ---- MCU 본체 ----
MX0, MX1, MY0, MY1 = 540, 830, 180, 890
box(MX0, MY0, MX1 - MX0, MY1 - MY0, "#f8fafc")
txt((MX0 + MX1) / 2.0, MY0 + 34, "U1", 17, "middle", "700")
txt((MX0 + MX1) / 2.0, MY0 + 57, "ATmega328P-PU", 15, "middle", "700")
txt((MX0 + MX1) / 2.0, MY0 + 77, "28-pin PDIP / 16MHz", 12, "middle", "400",
    MUTE)

Y_PD7, Y_PC0 = 250, 290
Y_SW = (380, 440, 500, 560)
Y_PB1 = 640
Y_PD0, Y_PD1 = 710, 746
Y_PC4, Y_PC5 = 805, 841

LEFT_PINS = [("VCC", 7, 240), ("AVCC", 20, 280), ("AREF", 21, 320),
             ("RESET", 1, 390), ("XTAL1", 9, 470), ("XTAL2", 10, 530),
             ("GND", 8, 810), ("GND", 22, 845)]
RIGHT_PINS = [("PD7", 13, Y_PD7), ("PC0", 23, Y_PC0),
              ("PD2", 4, Y_SW[0]), ("PD3", 5, Y_SW[1]),
              ("PD4", 6, Y_SW[2]), ("PD5", 11, Y_SW[3]),
              ("PB1", 15, Y_PB1),
              ("PD0", 2, Y_PD0), ("PD1", 3, Y_PD1),
              ("PC4", 27, Y_PC4), ("PC5", 28, Y_PC5)]

for name, pin, y in LEFT_PINS:
    wire((MX0 - 60, y), (MX0, y))
    txt(MX0 + 10, y + 5, name, 13, "start", "600")
    txt(MX0 - 8, y - 7, str(pin), 11.5, "end", "400", MUTE)
for name, pin, y in RIGHT_PINS:
    wire((MX1, y), (MX1 + 60, y))
    txt(MX1 - 10, y + 5, name, 13, "end", "600")
    txt(MX1 + 8, y - 7, str(pin), 11.5, "start", "400", MUTE)

# 이 회로의 핵심 두 핀은 기능명을 함께 적는다
txt(MX1 - 10, Y_PD7 - 15, "(AIN1)", 11, "end", "600", ACCENT)
txt(MX1 - 10, Y_PC0 - 15, "(ADC0)", 11, "end", "600", ACCENT)

# ---- 전원부 (좌측) ----
RAIL_Y = 120
wire((150, RAIL_Y), (470, RAIL_Y))
vcc(305, RAIL_Y)
for x, ref, val in ((170, "C1", "100nF"), (260, "C2", "100nF"),
                    (350, "C3", "10uF")):
    dot(x, RAIL_Y)
    wire((x, RAIL_Y), (x, 290))
    _, cb = cap_v(x, 302, ref, val)
    wire((x, cb), (x, 348))
    gnd(x, 348)

# VCC / AVCC 급전
wire((470, RAIL_Y), (470, 280))
dot(470, RAIL_Y)
wire((470, 240), (MX0 - 60, 240))
dot(470, 240)
wire((470, 280), (MX0 - 60, 280))

# RESET 풀업
wire((440, RAIL_Y), (440, 178))
dot(440, RAIL_Y)
_, r1b = resistor_v(440, 208, "R1", "10kΩ", "left")
wire((440, r1b), (440, 390), (MX0 - 60, 390))

# AREF 미사용
txt(MX0 - 70, 325, "N.C.", 12.5, "end", "600", MUTE)
line(MX0 - 68, 313, MX0 - 56, 327, 2, MUTE)
line(MX0 - 68, 327, MX0 - 56, 313, 2, MUTE)

# 클럭
wire((490, 470), (MX0 - 60, 470))
wire((490, 530), (MX0 - 60, 530))
yt, yb = crystal_v(490, 500, "Y1", "16MHz")
wire((490, 470), (490, yt))
wire((490, yb), (490, 530))

dot(490, 470)
wire((490, 470), (300, 470), (300, 545))
_, c4b = cap_v(300, 557, "C4", "22pF", "left")
wire((300, c4b), (300, 605))
gnd(300, 605)

dot(490, 530)
wire((490, 530), (430, 530), (430, 620))
_, c5b = cap_v(430, 632, "C5", "22pF", "left")
wire((430, c5b), (430, 680))
gnd(430, 680)

# GND 핀 2개 묶기
wire((MX0 - 60, 810), (430, 810))
wire((MX0 - 60, 845), (430, 845))
wire((430, 810), (430, 880))
dot(430, 845)
gnd(430, 880)

# ---- 피에조 입력부 (핵심 회로) ----
# PD7 을 주선으로 그리고 PC0 을 거기에 탭으로 붙인다.
# 두 핀을 같은 x 까지 나란히 끌면 닫힌 사각형처럼 보여 오독을 부른다.
PZ_Y = 250
wire((MX1 + 60, Y_PD7), (1043, PZ_Y))
wire((MX1 + 60, Y_PC0), (930, Y_PC0), (930, PZ_Y))
dot(930, PZ_Y)

r3a, r3b = resistor_h(1080, PZ_Y, "R3", "1kΩ")
CLAMP_X = 1180
wire((r3b, PZ_Y), (CLAMP_X, PZ_Y))
dot(CLAMP_X, PZ_Y)

# 과전압 클램프 (노드 -> +5V)
wire((CLAMP_X, PZ_Y), (CLAMP_X, 218))
d2t, _ = diode_v(CLAMP_X, 203, "D2", "1N4148", "left")
wire((CLAMP_X, d2t), (CLAMP_X, 176))
vcc(CLAMP_X, 176)

# 음의 스윙 클램프 (GND -> 노드)
wire((CLAMP_X, PZ_Y), (CLAMP_X, 290))
_, d3b = diode_v(CLAMP_X, 305, "D3", "1N4148", "left")
wire((CLAMP_X, d3b), (CLAMP_X, 355))
gnd(CLAMP_X, 355)

# 블리드 저항 + 피에조 본체
PZ_NODE_X = 1290
wire((CLAMP_X, PZ_Y), (PZ_NODE_X, PZ_Y))
dot(PZ_NODE_X, PZ_Y)
wire((PZ_NODE_X, PZ_Y), (PZ_NODE_X, 295))
_, r4b2 = resistor_v(PZ_NODE_X, 325, "R4", "1MΩ")
wire((PZ_NODE_X, r4b2), (PZ_NODE_X, 392))
gnd(PZ_NODE_X, 392)

BZ_X = 1420
wire((PZ_NODE_X, PZ_Y), (BZ_X, PZ_Y))
wire((BZ_X, PZ_Y), (BZ_X, 290))
_, bzb = piezo_v(BZ_X, 303, "BZ1", "압전 디스크")
wire((BZ_X, bzb), (BZ_X, 380))
gnd(BZ_X, 380)

# ---- 택트 스위치 4개 ----
for i, y in enumerate(Y_SW):
    wire((MX1 + 60, y), (900, y))
    sa, sb = switch_h(900, y, "SW%d" % (i + 1))
    wire((sb, y), (1055, y))
    gnd(1055, y)
txt(900, 340, "SW1~SW4 = KEY1~KEY4", 12.5, "start", "700", MUTE)
txt(900, 358, "내부 풀업 사용 — 외부 저항 없음", 12, "start", "400", MUTE)

# ---- 액추에이터 / 상태 표시 ----
wire((MX1 + 60, Y_PB1), (943, Y_PB1))
_, r2b = resistor_h(980, Y_PB1, "R2", "330Ω")
wire((r2b, Y_PB1), (1060, Y_PB1))
_, d1b = led_h(1060, Y_PB1, "D1", "LOCK 표시")
wire((d1b, Y_PB1), (1150, Y_PB1))
gnd(1150, Y_PB1)
txt(1210, Y_PB1 + 5, "인증 성공 시 HIGH.", 12, "start", "400", MUTE)
txt(1210, Y_PB1 + 23, "서보 신호선으로 대체 가능", 12, "start", "400", MUTE)

# ---- UART ----
connector(900, 682, 150, 92, "J1", "UART (보드 USB)",
          [("RXD", Y_PD0), ("TXD", Y_PD1)])
wire((MX1 + 60, Y_PD0), (900, Y_PD0))
wire((MX1 + 60, Y_PD1), (900, Y_PD1))
txt(1065, Y_PD0 + 5, "38400 8N1", 12, "start", "400", MUTE)

# ---- OLED 모듈 ----
OL_X, OL_Y, OL_W, OL_H = 1150, 760, 240, 150
connector(OL_X, OL_Y, OL_W, OL_H, "J2", "SSD1306 OLED 128x64",
          [("VCC", 785), ("GND", 815), ("SDA", 845), ("SCL", 875)])
wire((OL_X, 785), (1110, 785))
vcc(1110, 785)
wire((OL_X, 815), (1110, 815))
gnd(1110, 815)
wire((MX1 + 60, Y_PC4), (1080, Y_PC4), (1080, 845), (OL_X, 845))
wire((MX1 + 60, Y_PC5), (1055, Y_PC5), (1055, 875), (OL_X, 875))
txt(OL_X + OL_W / 2.0, OL_Y + OL_H - 14, "I2C 0x3C (제품에 따라 0x3D)",
    11.5, "middle", "400", MUTE)

# ---- 보드 핀 대응표 ----
txt(170, 950, "보드 핀 대응 (Arduino Uno 기준)", 13.5, "start", "700")
line(170, 960, 470, 960, 1.4)
MAPPING = [("PD2 / PD3 / PD4 / PD5", "D2 / D3 / D4 / D5  (SW1~4)"),
           ("PD7  (AIN1)", "D7   피에조 — 시각"),
           ("PC0  (ADC0)", "A0   피에조 — 진폭"),
           ("PB1", "D9   액추에이터 / LED"),
           ("PC4 / PC5", "A4 / A5  OLED SDA / SCL"),
           ("PD0 / PD1", "D0 / D1  UART RX / TX")]
for i, (a, b) in enumerate(MAPPING):
    yy = 984 + i * 21
    txt(170, yy, a, 12.5, "start", "600", "#3f3f46")
    txt(340, yy, "→", 12.5, "start", "400", "#a1a1aa")
    txt(364, yy, b, 12.5, "start", "400", "#3f3f46")

txt(170, 1140, "사용 핀 10개 / ATmega328P 가용 I/O 23개", 12.5, "start",
    "700", MUTE)

# ---- 보드 실장 안내 ----
box(560, 928, 520, 104, "#fffbeb", "#a16207", 1.6)
txt(576, 952, "※ Arduino Uno 보드를 쓰는 경우", 13, "start", "700", "#713f12")
for i, s2 in enumerate((
        "U1, Y1, C1~C5, R1 은 보드에 이미 실장되어 있어 배선하지 않는다.",
        "브레드보드에 실제로 꽂는 것은 SW1~SW4, BZ1, R2·R3·R4,",
        "D1~D3, J2(OLED) 뿐이다. J1(UART)은 보드의 USB 단자가 대신한다.")):
    txt(576, 976 + i * 20, s2, 12, "start", "400", "#713f12")

# ---- 설계 요점 ----
box(560, 1046, 520, 164, "#faf5ff", ACCENT, 1.6)
txt(576, 1070, "※ 이 회로의 핵심", 13, "start", "700", ACCENT)
NOTES = [
    ("PD7 = 비교기 음극 입력 → Timer1 입력 캡처로 노크 '시각' 측정",
     ACCENT, "700"),
    ("PC0 = ADC 입력 → 같은 노드에서 노크 '진폭' 측정", ACCENT, "700"),
    ("ACME=0 이어야 비교기와 ADC 를 동시에 쓸 수 있으므로,", INK, "400"),
    ("한 노드에서 선을 두 가닥 뽑아 두 핀에 각각 연결한다.", INK, "400"),
    ("R4(1MΩ)가 없으면 압전 전하가 빠지지 못해 노드 전위가 표류하고,",
     WARN, "400"),
    ("두 번째 노크부터 문턱을 넘지 못한다. 반드시 넣을 것.", WARN, "400"),
]
for i, (t, c, w) in enumerate(NOTES):
    txt(576, 1094 + i * 20, t, 12, "start", w, c)

# ---- 표제란 ----
TB_X, TB_Y = 1090, 1075
box(TB_X, TB_Y, 450, 128)
line(TB_X, TB_Y + 32, TB_X + 450, TB_Y + 32, 1.4)
line(TB_X, TB_Y + 68, TB_X + 450, TB_Y + 68, 1.4)
line(TB_X, TB_Y + 98, TB_X + 450, TB_Y + 98, 1.4)
line(TB_X + 300, TB_Y + 68, TB_X + 300, TB_Y + 128, 1.4)
txt(TB_X + 12, TB_Y + 23, "버튼 시퀀스 · 노크 리듬 기반 이중 인증 잠금 시스템",
    12.5, "start", "700")
txt(TB_X + 12, TB_Y + 57, "회로도 — 전체 시스템", 14.5, "start", "700")
txt(TB_X + 12, TB_Y + 88, "2026 COSS MCU 응용 경진대회", 11.5, "start", "400",
    "#52525b")
txt(TB_X + 12, TB_Y + 118, "설계: (팀명 기입)", 11.5, "start", "400",
    "#52525b")
txt(TB_X + 312, TB_Y + 88, "Rev. 1.0", 11.5, "start", "400", "#52525b")
txt(TB_X + 312, TB_Y + 118, "Sheet 1 / 1", 11.5, "start", "400", "#52525b")

add('</svg>')

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
outdir = os.path.join(root, "figures")
if not os.path.isdir(outdir):
    os.makedirs(outdir)
path = os.path.join(outdir, "schematic.svg")
doc = "\n".join(out)
# 저장 전 XML 검증. 깨진 SVG 를 그대로 내보내면 브라우저가 오류 페이지를
# 렌더링하고, 그 화면이 그대로 제출용 PDF 에 들어가 버린다.
ET.fromstring(doc)
io.open(path, "w", encoding="utf-8").write(doc)
print("생성 완료: %s (%d bytes, XML 검증 통과)"
      % (path, os.path.getsize(path)))
