# -*- coding: utf-8 -*-
"""
make_figures.py — 발표자료용 그림 생성기

출력:
  figures/fig1_block.svg  시스템 블록도
  figures/fig2_flow.svg   프로그램 흐름 (인증 상태 기계)

회로도(make_schematic.py)와 같은 색·글꼴 규약을 쓴다.
실행:  python tools/make_figures.py
"""

import io
import os
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

FONT = "'Malgun Gothic','맑은 고딕','Noto Sans KR',sans-serif"
INK = "#1e293b"
MUTE = "#64748b"
ACCENT = "#7c3aed"
WARN = "#b91c1c"
OK = "#047857"
HW = "#0e7490"      # 하드웨어 블록
SW = "#4338ca"      # 소프트웨어 블록


class Fig(object):
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.o = []
        self.o.append(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
            'width="%d" height="%d" font-family="%s">' % (w, h, w, h, FONT))
        self.o.append(
            '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            '<path d="M 0 0 L 10 5 L 0 10 z" fill="%s"/></marker>'
            '<marker id="arw" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            '<path d="M 0 0 L 10 5 L 0 10 z" fill="%s"/></marker></defs>'
            % (INK, WARN))
        self.o.append('<rect width="%d" height="%d" fill="#ffffff"/>' % (w, h))

    def add(self, s):
        self.o.append(s)

    def txt(self, x, y, s, size=14, anchor="middle", weight="400", color=INK):
        # 본문에 <, >, & 가 섞이면 SVG(XML)가 통째로 깨진다. 반드시 이스케이프.
        self.add('<text x="%g" y="%g" font-size="%g" text-anchor="%s" '
                 'font-weight="%s" fill="%s">%s</text>'
                 % (x, y, size, anchor, weight, color, escape(s)))

    def box(self, x, y, w, h, fill="#ffffff", stroke=INK, sw=2, rx=8):
        self.add('<rect x="%g" y="%g" width="%g" height="%g" rx="%g" '
                 'fill="%s" stroke="%s" stroke-width="%g"/>'
                 % (x, y, w, h, rx, fill, stroke, sw))

    def node(self, x, y, w, h, lines, fill="#ffffff", stroke=INK,
             title_size=15, body_size=12, rx=8):
        """가운데 정렬 여러 줄 블록. lines = [(텍스트, 크기, 굵기, 색), ...]"""
        self.box(x, y, w, h, fill, stroke, 2, rx)
        total = sum(l[1] + 6 for l in lines) - 6
        cy = y + h / 2.0 - total / 2.0
        for t, size, weight, color in lines:
            cy += size
            self.txt(x + w / 2.0, cy, t, size, "middle", weight, color)
            cy += 6

    def arrow(self, pts, color=INK, label=None, lx=0, ly=0, dashed=False,
              marker="ar"):
        d = " ".join("%g,%g" % p for p in pts)
        dash = ' stroke-dasharray="7 5"' if dashed else ""
        self.add('<polyline points="%s" fill="none" stroke="%s" '
                 'stroke-width="2.2" stroke-linejoin="round"%s '
                 'marker-end="url(#%s)"/>' % (d, color, dash, marker))
        if label:
            self.txt(lx, ly, label, 12, "middle", "600", color)

    def save(self, path):
        self.add('</svg>')
        doc = "\n".join(self.o)
        # 저장 전에 XML 로 파싱해 본다. 깨진 SVG 를 그대로 내보내면 브라우저가
        # 오류 페이지를 렌더링하고, 그 화면이 그대로 PPT 에 들어가 버린다.
        ET.fromstring(doc)
        io.open(path, "w", encoding="utf-8").write(doc)
        print("생성: %s (%d bytes, XML 검증 통과)"
              % (path, os.path.getsize(path)))


# ============================ 그림 1: 블록도 ============================

def fig_block(path):
    f = Fig(1500, 860)

    f.txt(750, 44, "시스템 블록도", 22, "middle", "700")
    f.txt(750, 70, "파란 테두리 = 하드웨어(주변장치) / 보라 테두리 = 소프트웨어",
          13, "middle", "400", MUTE)

    # ---- 입력부 (좌측) ----
    f.txt(150, 118, "입력", 14, "middle", "700", MUTE)
    f.node(40, 135, 220, 92, [
        ("택트 스위치 4개", 15, "700", INK),
        ("PD2~PD5 · 내부 풀업", 12, "400", MUTE)], "#f0f9ff", HW)
    f.node(40, 300, 220, 108, [
        ("압전(피에조) 디스크", 15, "700", INK),
        ("1MΩ 블리드 + 1kΩ 보호", 12, "400", MUTE),
        ("+ 클램프 다이오드", 12, "400", MUTE)], "#f0f9ff", HW)

    # ---- MCU 주변장치 (중앙 좌) ----
    f.box(320, 100, 800, 620, "#fafafa", MUTE, 2, 12)
    f.txt(720, 128, "ATmega328P  (16MHz · Bare-Metal)", 16, "middle", "700",
          MUTE)

    f.node(350, 150, 230, 74, [
        ("GPIO 폴링 + 디바운스", 13.5, "700", INK),
        ("keypad.c", 12, "400", MUTE)], "#f0f9ff", HW)

    f.node(350, 290, 230, 88, [
        ("Analog Comparator", 13.5, "700", INK),
        ("내부 1.1V 밴드갭 기준", 12, "400", MUTE),
        ("ACIC=1", 12, "600", ACCENT)], "#f0f9ff", HW)
    f.node(350, 400, 230, 88, [
        ("Timer1 Input Capture", 13.5, "700", INK),
        ("ICR1 하드웨어 래치", 12, "400", MUTE),
        ("분해능 500ns", 12, "600", ACCENT)], "#f0f9ff", HW)
    f.node(350, 510, 230, 74, [
        ("ADC0  (8bit / 1MHz)", 13.5, "700", INK),
        ("노크 진폭 게이트", 12, "400", MUTE)], "#f0f9ff", HW)

    # ---- 소프트웨어 (중앙 우) ----
    f.node(640, 150, 230, 74, [
        ("순서 대조", 13.5, "700", INK),
        ("1단계 · 지식", 12, "600", OK)], "#f5f3ff", SW)

    f.node(640, 330, 230, 88, [
        ("링잉 불응기 50ms", 13.5, "700", INK),
        ("간격 벡터 [t1,t2,t3]", 12, "400", MUTE),
        ("knock.c", 12, "400", MUTE)], "#f5f3ff", SW)
    f.node(640, 440, 230, 88, [
        ("템포 정규화", 13.5, "700", INK),
        ("비율 벡터 (합=1000)", 12, "400", MUTE),
        ("knockfp.c", 12, "400", MUTE)], "#f5f3ff", SW)
    f.node(640, 550, 230, 88, [
        ("최근접 중심점 분류", 13.5, "700", INK),
        ("32비트 정수 · float 없음", 12, "400", MUTE),
        ("classify.c  (재사용)", 12, "600", OK)], "#f5f3ff", SW)

    # ---- 판정 ----
    f.node(920, 300, 170, 130, [
        ("2단계 동시 성립", 14, "700", INK),
        ("판정", 20, "700", ACCENT),
        ("PIN 사용자", 12, "400", MUTE),
        ("== 리듬 사용자", 12, "600", ACCENT)], "#faf5ff", ACCENT, rx=14)

    # ---- EEPROM ----
    f.node(640, 660, 230, 46, [
        ("EEPROM 40B — 등록정보 · 실패 카운터", 12.5, "700", INK)],
        "#fffbeb", "#a16207")

    # ---- 출력부 (우측) ----
    f.txt(1310, 118, "출력", 14, "middle", "700", MUTE)
    f.node(1180, 150, 250, 74, [
        ("OLED SSD1306", 15, "700", INK),
        ("I2C · 상태 표시", 12, "400", MUTE)], "#f0f9ff", HW)
    f.node(1180, 320, 250, 90, [
        ("액추에이터 / LED", 15, "700", INK),
        ("PB1 · 잠금 해제", 12, "400", MUTE),
        ("3초 후 자동 잠금", 12, "400", MUTE)], "#f0f9ff", HW)
    f.node(1180, 500, 250, 90, [
        ("UART 38400 8N1", 15, "700", INK),
        ("CSV 로그 → PC", 12, "400", MUTE),
        ("실험 3·4 데이터 수집", 12, "600", OK)], "#f0f9ff", HW)

    # ---- 배선 ----
    f.arrow([(260, 181), (350, 181)])
    f.arrow([(260, 340), (310, 340), (310, 334), (350, 334)])
    f.arrow([(260, 380), (310, 380), (310, 554), (350, 554)])
    f.arrow([(465, 378), (465, 400)], ACCENT)
    f.arrow([(580, 187), (640, 187)])
    f.arrow([(580, 444), (610, 444), (610, 374), (640, 374)])
    f.arrow([(580, 547), (610, 547), (610, 400), (640, 400)],
            dashed=True)
    f.arrow([(755, 418), (755, 440)], ACCENT)
    f.arrow([(755, 528), (755, 550)], ACCENT)
    f.arrow([(870, 187), (895, 187), (895, 330), (920, 330)], OK)
    f.arrow([(870, 594), (895, 594), (895, 400), (920, 400)], OK)
    f.arrow([(755, 660), (755, 638)], "#a16207")
    f.arrow([(1090, 340), (1180, 340)], ACCENT)
    f.arrow([(1090, 320), (1140, 320), (1140, 187), (1180, 187)])
    f.arrow([(1090, 410), (1140, 410), (1140, 545), (1180, 545)])

    # 라벨
    f.txt(305, 168, "키 입력", 11.5, "middle", "600", MUTE)
    f.txt(305, 322, "노크 전압", 11.5, "middle", "600", MUTE)
    f.txt(600, 300, "시각", 11.5, "middle", "600", ACCENT)
    f.txt(600, 470, "진폭", 11.5, "middle", "600", MUTE)
    f.txt(897, 262, "순서 일치 사용자", 11, "middle", "600", OK)
    f.txt(897, 640, "리듬 일치 사용자", 11, "middle", "600", OK)

    # 하단 설명
    f.box(40, 750, 1420, 78, "#faf5ff", ACCENT, 1.8, 10)
    f.txt(60, 776, "핵심: 두 인증 계층이 서로 다른 주변장치에서 독립적으로 "
                   "얻어지고, 두 결과가 같은 사용자를 가리켜야만 해제된다.",
          13.5, "start", "700", ACCENT)
    f.txt(60, 802, "따라서 버튼 순서가 노출되어도, 리듬을 흉내내도, "
                   "한쪽만으로는 잠금을 풀 수 없다.",
          13, "start", "400", INK)

    f.save(path)


# ========================= 그림 2: 프로그램 흐름 =========================

def fig_flow(path):
    f = Fig(1500, 900)

    f.txt(750, 44, "프로그램 흐름 — 인증 상태 기계", 22, "middle", "700")
    f.txt(750, 70, "붉은 화살표 = 실패 경로 / 굵은 테두리 = 보안상 중요한 순서",
          13, "middle", "400", MUTE)

    def st(x, y, w, h, lines, fill="#ffffff", stroke=INK, rx=8):
        f.node(x, y, w, h, lines, fill, stroke, rx=rx)

    # 좌측 주 흐름
    st(80, 110, 240, 66, [("전원 투입 / 부팅", 14, "700", INK)], "#f8fafc")
    st(80, 216, 240, 86, [
        ("EEPROM 실패 카운터 확인", 13, "700", INK),
        ("값 ^ 보수 != 0xFF 이면 손상", 11.5, "400", MUTE)], "#fffbeb",
        "#a16207")
    st(80, 342, 240, 66, [("대기 (IDLE)", 15, "700", INK)], "#f8fafc")
    st(80, 448, 240, 86, [
        ("1단계 · 버튼 순서 입력", 13.5, "700", INK),
        ("4자리 · 10초 무입력 시 취소", 11.5, "400", MUTE)], "#eff6ff")

    st(80, 574, 240, 96, [
        ("실패 카운터 +1", 14, "700", WARN),
        ("평가하기 전에 먼저 기록", 11.5, "700", WARN),
        ("전원 차단 회피 방지", 11.5, "400", MUTE)], "#fef2f2", WARN, rx=8)

    st(80, 710, 240, 96, [
        ("2단계 · 노크 4회 수신", 13.5, "700", INK),
        ("비교기 → Timer1 캡처", 11.5, "400", MUTE),
        ("6초 무입력 시 취소", 11.5, "400", MUTE)], "#eff6ff")

    # 중앙 처리
    st(430, 574, 250, 96, [
        ("링잉 불응기 50ms 적용", 13, "700", INK),
        ("진폭 < 70 이면 노크 무시", 11.5, "400", MUTE),
        ("→ 간격 벡터 [t1,t2,t3]", 11.5, "600", ACCENT)], "#f5f3ff", SW)
    st(430, 710, 250, 96, [
        ("템포 정규화", 13, "700", INK),
        ("비율 벡터 (합 = 1000)", 11.5, "400", MUTE),
        ("범위 밖이면 즉시 거부", 11.5, "600", WARN)], "#f5f3ff", SW)

    st(790, 710, 250, 96, [
        ("최근접 중심점 분류", 13, "700", INK),
        ("정수 제곱거리 비교", 11.5, "400", MUTE),
        ("임계값 초과 시 -1", 11.5, "400", MUTE)], "#f5f3ff", SW)

    # 판정
    st(790, 540, 250, 120, [
        ("판정", 18, "700", ACCENT),
        ("PIN 사용자 >= 0  그리고", 12, "400", INK),
        ("리듬 사용자 == PIN 사용자", 12, "700", ACCENT)],
        "#faf5ff", ACCENT, rx=14)

    # 성공 / 실패
    st(1160, 430, 250, 110, [
        ("해제 (GRANTED)", 15, "700", OK),
        ("실패 카운터 0 으로 복귀", 12, "400", INK),
        ("3초 후 자동 잠금", 12, "400", MUTE)], "#ecfdf5", OK)
    st(1160, 600, 250, 96, [
        ("거부 (DENIED)", 15, "700", WARN),
        ("남은 시도 횟수 표시", 12, "400", INK)], "#fef2f2", WARN)
    st(1160, 740, 250, 110, [
        ("잠금 (LOCKOUT)", 15, "700", WARN),
        ("5회 연속 실패 → 30초 대기", 12, "400", INK),
        ("전원 재인가로 회피 불가", 12, "700", WARN)], "#fef2f2", WARN, rx=8)

    # 등록 분기
    st(430, 342, 250, 96, [
        ("등록 (ENROLL)", 14, "700", INK),
        ("순서 4자리 + 리듬 5회 반복", 11.5, "400", MUTE),
        ("임계값을 흩어짐에서 자동 유도", 11.5, "600", ACCENT)],
        "#f8fafc", MUTE)
    st(790, 342, 250, 96, [
        ("EEPROM 저장", 14, "700", INK),
        ("체크섬 포함 38바이트", 11.5, "400", MUTE),
        ("흩어짐 과다 시 저장 거부", 11.5, "600", WARN)], "#fffbeb", "#a16207")

    # ---- 화살표 ----
    f.arrow([(200, 176), (200, 216)])
    f.arrow([(200, 302), (200, 342)])
    f.arrow([(200, 408), (200, 448)])
    f.arrow([(200, 534), (200, 574)])
    f.arrow([(200, 670), (200, 710)])
    f.arrow([(320, 758), (390, 758), (390, 622), (430, 622)])
    f.arrow([(555, 670), (555, 710)])
    f.arrow([(680, 758), (790, 758)])
    f.arrow([(915, 710), (915, 660)])
    f.arrow([(1040, 580), (1100, 580), (1100, 485), (1160, 485)], OK,
            "성립", 1100, 470)
    f.arrow([(1040, 620), (1100, 620), (1100, 648), (1160, 648)], WARN,
            "불성립", 1103, 690, marker="arw")
    f.arrow([(1285, 696), (1285, 740)], WARN, "5회 누적", 1360, 722,
            marker="arw")

    # 등록 경로
    f.arrow([(320, 375), (430, 375)], MUTE, "KEY1 길게", 375, 362)
    f.arrow([(680, 390), (790, 390)], MUTE)
    f.arrow([(915, 342), (915, 300), (200, 300), (200, 330)], MUTE,
            dashed=True)
    f.txt(560, 292, "등록 완료 후 대기로 복귀", 11.5, "middle", "600", MUTE)

    # 재등록 제한
    f.arrow([(1285, 430), (1285, 250), (555, 250), (555, 336)], OK,
            dashed=True)
    f.txt(900, 242, "재등록은 인증 성공 직후에만 허용 (KEY1 길게)",
          12, "middle", "700", OK)

    f.save(path)


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outdir = os.path.join(root, "figures")
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    fig_block(os.path.join(outdir, "fig1_block.svg"))
    fig_flow(os.path.join(outdir, "fig2_flow.svg"))
