# -*- coding: utf-8 -*-
"""
make_ppt.py — 예선 보고서 PPT 초안 생성기

제출물 「가. 보고서(PPT)」의 골격을 실제 pptx 파일로 만든다.
운영설명 PDF 「4-가」의 7개 필수 항목과 1:1 대응시킨다.

  1) 시스템의 기능·동작 원리·구조      -> 슬라이드 5, 6
  2) 시스템 구현 전략                  -> 슬라이드 7, 8, 9, 16
  3) 시스템 설계 및 실험 과정          -> 슬라이드 10~14, 17, 18
  4) 단위별 상세 설명                  -> 슬라이드 8, 10~15
  5) 해결하지 못한 부분                -> 슬라이드 21
  6) 메모리 사용량 화면 캡처           -> 슬라이드 19
  7) 부품 가격표                       -> 슬라이드 20

실측이 필요한 장(17·18·19)은 붉은 안내 상자를 넣어 비워둔다.
측정이 끝난 뒤 그 상자만 그래프·캡처로 교체하면 된다.

실행:  python tools/make_ppt.py
출력:  제출물/가_예선보고서_초안.pptx

주의: 그림 PNG 가 먼저 있어야 한다. 없으면 sh tools/render_figures.sh 실행.
"""

import os

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

# ---------------------------- 공통 설정 ----------------------------

FONT = "맑은 고딕"
INK = RGBColor(0x1E, 0x29, 0x3B)
MUTED = RGBColor(0x64, 0x74, 0x8B)
ACCENT = RGBColor(0x7C, 0x3A, 0xED)
WARN = RGBColor(0xB9, 0x1C, 0x1C)
OK = RGBColor(0x04, 0x78, 0x57)
BAND = RGBColor(0x7C, 0x3A, 0xED)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

SW, SH = 13.333, 7.5  # 16:9 인치

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PNG = os.path.join(ROOT, "figures", "png")


def set_font(run, size, bold=False, color=INK):
    """한글이 깨지지 않도록 라틴·동아시아 글꼴을 모두 지정한다.

    run.font.name 은 <a:latin> 만 건드린다. 한글은 <a:ea> 를 따르므로
    이것을 함께 지정하지 않으면 PowerPoint 가 기본 글꼴로 대체해버린다.
    """
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = FONT

    rPr = run.font._element
    for tag in ("ea", "cs"):
        q = qn("a:" + tag)
        el = rPr.find(q)
        if el is None:
            el = rPr.makeelement(q, {})
            rPr.append(el)
        el.set("typeface", FONT)


def textbox(slide, x, y, w, h):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    return tf


def para(tf, text, size=16, bold=False, color=INK, space_after=6,
         level=0, first=False, align=PP_ALIGN.LEFT):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.level = level
    p.space_after = Pt(space_after)
    run = p.add_run()
    run.text = text
    set_font(run, size, bold, color)
    return p


def rect(slide, x, y, w, h, fill, line=None):
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y),
                                Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(1)
    sh.shadow.inherit = False
    return sh


def new_slide(prs, title, tag=None, num=None, sub=None):
    """제목 띠가 있는 기본 슬라이드."""
    s = prs.slides.add_slide(prs.slide_layouts[6])
    rect(s, 0, 0, SW, 1.02, RGBColor(0xF8, 0xFA, 0xFC))
    rect(s, 0, 1.00, SW, 0.045, BAND)

    tf = textbox(s, 0.55, 0.10, 9.6, 0.55)
    para(tf, title, 25, True, INK, 0, first=True)
    if sub:
        tf_s = textbox(s, 0.58, 0.60, 9.6, 0.36)
        para(tf_s, sub, 13, False, MUTED, 0, first=True)

    if tag:
        tf2 = textbox(s, 9.9, 0.28, 3.0, 0.5)
        para(tf2, tag, 12.5, True, BAND, 0, first=True, align=PP_ALIGN.RIGHT)
    if num is not None:
        tf3 = textbox(s, 12.4, 6.92, 0.7, 0.4)
        para(tf3, str(num), 11, False, MUTED, 0, first=True,
             align=PP_ALIGN.RIGHT)
    return s


def bullets(slide, items, x=0.75, y=1.45, w=11.9, size=17):
    """items: (텍스트, 레벨, 강조여부) 튜플 목록."""
    tf = textbox(slide, x, y, w, SH - y - 0.6)
    for i, (text, lvl, strong) in enumerate(items):
        color = ACCENT if strong else INK
        para(tf, text, size - lvl * 2.5, strong, color,
             space_after=10 if lvl == 0 else 5, level=lvl, first=(i == 0))
    return tf


def note_box(slide, lines, x=0.75, y=5.55, w=11.9, h=1.3,
             fill=RGBColor(0xFF, 0xFB, 0xEB), line=RGBColor(0xA1, 0x62, 0x07),
             color=RGBColor(0x71, 0x3F, 0x12), size=13):
    rect(slide, x, y, w, h, fill, line)
    tf = textbox(slide, x + 0.22, y + 0.11, w - 0.44, h - 0.22)
    for i, t in enumerate(lines):
        para(tf, t, size, i == 0, color, 3, first=(i == 0))


def todo_box(slide, lines, x=0.75, y=2.1, w=11.9, h=3.2):
    """실험·측정 후 채울 자리."""
    note_box(slide, lines, x=x, y=y, w=w, h=h,
             fill=RGBColor(0xFE, 0xF2, 0xF2), line=WARN, color=WARN, size=14)


def table(slide, headers, rows, x=0.75, y=1.5, w=11.9, h=None, fs=13):
    nr, nc = len(rows) + 1, len(headers)
    h = h or min(0.4 * nr + 0.1, SH - y - 0.5)
    shape = slide.shapes.add_table(nr, nc, Inches(x), Inches(y),
                                   Inches(w), Inches(h))
    tbl = shape.table
    for c, head in enumerate(headers):
        cell = tbl.cell(0, c)
        cell.text = ""
        para(cell.text_frame, head, fs, True, WHITE, 0, first=True)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(0x33, 0x41, 0x55)
    for r, row in enumerate(rows, start=1):
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.text = ""
            strong = val.startswith("*")
            para(cell.text_frame, val.lstrip("*"), fs, strong,
                 ACCENT if strong else INK, 0, first=True)
            cell.fill.solid()
            cell.fill.fore_color.rgb = (WHITE if r % 2
                                        else RGBColor(0xF1, 0xF5, 0xF9))
    return tbl


def picture(slide, name, x, y, w=None, h=None):
    path = os.path.join(PNG, name)
    if not os.path.exists(path):
        tf = textbox(slide, x, y, 8, 0.6)
        para(tf, "[그림 없음: %s — sh tools/render_figures.sh 실행]" % name,
             13, True, WARN, 0, first=True)
        return None
    kw = {}
    if w:
        kw["width"] = Inches(w)
    if h:
        kw["height"] = Inches(h)
    return slide.shapes.add_picture(path, Inches(x), Inches(y), **kw)


def code_box(slide, lines, x=0.75, y=1.5, w=6.0, h=3.4, title=None):
    """코드 인용 상자. 고정폭 글꼴로 표시한다."""
    rect(slide, x, y, w, h, RGBColor(0x0F, 0x17, 0x2A))
    tf = textbox(slide, x + 0.16, y + 0.10, w - 0.32, h - 0.20)
    if title:
        p = para(tf, title, 11.5, True, RGBColor(0xA7, 0x8B, 0xFA), 4,
                 first=True)
        first_done = True
    else:
        first_done = False
    for i, t in enumerate(lines):
        p = para(tf, t, 11, False, RGBColor(0xE2, 0xE8, 0xF0), 1,
                 first=(not first_done and i == 0))
        for run in p.runs:
            run.font.name = "Consolas"
    return tf


# ---------------------------- 슬라이드 조립 ----------------------------

def build():
    prs = Presentation()
    prs.slide_width = Inches(SW)
    prs.slide_height = Inches(SH)
    n = [0]

    def num():
        n[0] += 1
        return n[0]

    # ---------------- 1. 표지 ----------------
    s = prs.slides.add_slide(prs.slide_layouts[6])
    rect(s, 0, 0, SW, SH, RGBColor(0x0F, 0x17, 0x2A))
    rect(s, 0, 3.55, SW, 0.06, BAND)
    tf = textbox(s, 1.1, 1.80, 11.2, 1.7)
    para(tf, "버튼 시퀀스 · 노크 리듬 기반", 34, True, WHITE, 8, first=True)
    para(tf, "저비용 이중 인증(2FA) 잠금 시스템", 34, True, WHITE, 0)
    tf = textbox(s, 1.1, 3.85, 11.2, 1.5)
    para(tf, "추가 부품 1개(압전 디스크)로 '지식 + 행동' 두 계층을 구현한다",
         17, False, RGBColor(0xC4, 0xB5, 0xFD), 10, first=True)
    para(tf, "ATmega328P · Bare-Metal · 라이브러리 미사용",
         15, False, RGBColor(0x94, 0xA3, 0xB8), 0)
    tf = textbox(s, 1.1, 6.05, 11.2, 1.0)
    para(tf, "2026 COSS 차세대반도체 MCU 응용 경진대회 (대학생부)",
         14, True, RGBColor(0x94, 0xA3, 0xB8), 6, first=True)
    para(tf, "팀명 / 소속 / 성명 기입", 13, False, RGBColor(0x64, 0x74, 0x8B), 0)

    # ---------------- 2. 한 장 요약 ----------------
    s = new_slide(prs, "한 장 요약", "Executive Summary", num())
    bullets(s, [
        ("무엇을 만들었나", 0, True),
        ("버튼 4개를 정해진 순서로 누르는 '지식' 인증과, 표면을 두드리는 "
         "리듬을 압전 소자로 재는 '행동' 인증을 결합한 잠금 장치", 1, False),
        ("두 인증이 서로 다른 주변장치에서 독립적으로 얻어지고, "
         "두 결과가 같은 사용자를 가리켜야만 해제된다", 1, False),
        ("왜 의미가 있나", 0, True),
        ("PIN 키패드는 어깨너머로 보면 뚫린다. 지문 모듈은 원가가 크다. "
         "그 사이를 부품 하나로 메운다", 1, False),
        ("무엇이 어려웠나", 0, True),
        ("리듬 인증은 '간격의 재현성'이 전부다. 측정 지터를 없애기 위해 "
         "아날로그 비교기 출력을 Timer1 입력 캡처에 직결했다 (분해능 500ns)",
         1, False),
        ("압전 소자의 공진(링잉)으로 노크 1회가 이벤트 여러 개로 잡히는 문제, "
         "템포가 달라지면 본인도 거부되는 문제를 각각 해결했다", 1, False),
    ], size=17)
    note_box(s, [
        "핵심 수치 — 사용 핀 10개 / Flash 8,908B (27.2%) / SRAM 110B (5.4%) "
        "/ EEPROM 40B / 신규 부품 4종",
        "전 구간 레지스터 직접 제어. 부동소수점 미사용으로 소프트 FP "
        "라이브러리(1.5~3KB)가 링크되지 않는다.",
    ], y=5.75, h=1.15)

    # ---------------- 3. 문제의식 ----------------
    s = new_slide(prs, "문제의식 — 저비용 잠금장치의 한계", "독창성 · 효용성",
                  num())
    table(s,
          ["방식", "한계", "원가"],
          [["버튼 PIN 키패드",
            "입력 순간을 보거나 버튼 마모 흔적만으로 순서가 유추됨", "매우 낮음"],
           ["RFID 카드", "카드 분실·복제 시 그대로 무력화", "낮음"],
           ["지문 / 얼굴 인식 모듈",
            "정확하지만 모듈 원가가 시스템 원가를 지배. "
            "8비트 MCU 로는 영상 처리 불가", "높음"],
           ["*본 제안 (순서 + 리듬)",
            "*순서를 알아도 리듬을 재현하지 못하면 열리지 않음",
            "*매우 낮음"]],
          y=1.55, fs=14)
    note_box(s, [
        "핵심 논점 — '관찰되지 않는다'가 아니라 '관찰되어도 재현되지 않는다'",
        "노크 리듬은 소리가 나므로 오히려 관찰하기 쉽다. 방어력의 근거는 "
        "은닉이 아니라 재현 난이도이며, 이것을 실험 4(타인 모사 시도)에서 "
        "정량적으로 증명한다.",
    ], y=4.55, h=1.25)
    note_box(s, [
        "선행 사례와의 차이",
        "노크 인식 잠금장치는 공개 사례가 있다. 본 작품은 (1) 지식 인증과 "
        "결합해 2FA 로 만들고, (2) 두 계층이 같은 사용자를 가리킬 것을 "
        "요구하며, (3) 임계값을 사용자 재현성에서 자동 유도하고, "
        "(4) 전원 차단 공격까지 대비한 점이 다르다.",
    ], y=5.95, h=1.15,
        fill=RGBColor(0xF5, 0xF3, 0xFF), line=ACCENT, color=ACCENT)

    # ---------------- 4. 제안 구조 ----------------
    s = new_slide(prs, "제안 — 서로 다른 성격의 증거 두 가지",
                  "독창성", num())
    table(s,
          ["", "1단계 · 지식 (Knowledge)", "2단계 · 행동 (Inherence)"],
          [["입력", "등록된 버튼 4개를 정해진 순서로",
            "표면을 두드리는 리듬 (간격 패턴)"],
           ["물리 채널", "디지털 GPIO (PD2~PD5)",
            "아날로그 비교기 + ADC (PD7 / PC0)"],
           ["판정", "순서 일치 여부", "정규화 벡터의 최근접 중심점 거리"],
           ["*공격 시나리오", "*어깨너머로 순서 노출", "*소리를 듣고 리듬 모방"],
           ["*방어", "*리듬이 달라 거부", "*순서를 몰라 거부"]],
          y=1.55, fs=14)
    note_box(s, [
        "두 계층은 AND 조건이 아니라 '같은 사용자를 가리켜야 한다'는 "
        "더 강한 조건으로 결합된다.",
        "사용자 A 의 순서와 사용자 B 의 리듬을 조합해도 통과하지 못한다.",
    ], y=5.35, h=1.05,
        fill=RGBColor(0xF5, 0xF3, 0xFF), line=ACCENT, color=ACCENT)

    # ---------------- 5. 기능과 동작 원리 ----------------
    s = new_slide(prs, "시스템의 기능과 동작 원리", "요강 4-가-1", num())
    bullets(s, [
        ("압전 효과 — 왜 노크를 전압으로 잴 수 있나", 0, True),
        ("압전 디스크는 기계적 충격을 받으면 순간적으로 전압을 만든다. "
         "이 전압이 내부 1.1V 밴드갭 기준을 넘는 순간을 '노크 이벤트'로 본다.",
         1, False),
        ("리듬의 수학적 표현", 0, True),
        ("노크 4회 → 간격 3개 [t1, t2, t3] → 총 길이로 나눈 비율 벡터 "
         "→ 등록된 중심점과의 제곱거리 비교", 1, False),
        ("등록 · 인증 흐름", 0, True),
        ("등록: 순서 4자리 입력 → 같은 리듬 5회 반복 → 평균이 중심점, "
         "흩어짐이 임계값", 1, False),
        ("인증: 순서 입력 → 실패 카운터 선증가 → 노크 수신 → 정규화 → 분류 "
         "→ 두 결과가 같은 사용자면 해제", 1, False),
    ], y=1.45, size=17)
    note_box(s, [
        "동작 조건 — 노크 간격 40ms 이상, 전체 연주 길이 150ms ~ 5,000ms, "
        "노크 진폭 ADC 70 이상 (≈1.37V)",
        "이 범위를 벗어난 입력은 분류기에 들어가기 전에 거부된다.",
    ], y=5.75, h=1.15)

    # ---------------- 6. 블록도 ----------------
    s = new_slide(prs, "시스템 블록도", "요강 4-가-1 · 4-가-2", num())
    picture(s, "fig1_block.png", 0.62, 1.30, w=12.1)

    # ---------------- 7. MCU · 부품 선정 근거 ----------------
    s = new_slide(prs, "MCU 및 부품 선정 근거", "요강 4-가-2", num())
    table(s,
          ["선택", "대안", "선정 이유"],
          [["*ATmega328P (16MHz)", "STM32F103 등",
            "요강 허용 MCU. 8비트로도 충분한 연산량이며 원가·소비전력이 낮다. "
            "필요한 주변장치(비교기+입력캡처)를 모두 내장한다."],
           ["*압전 디스크", "지문 모듈, 마이크",
            "부품 1개로 행동 인증을 추가. 광학 정렬·차광 같은 제약이 없고 "
            "표면에 붙이기만 하면 된다."],
           ["*비교기 + Timer1 입력 캡처", "ADC 폴링",
            "ICR1 래치가 하드웨어라 ISR 지연이 측정값에 섞이지 않는다. "
            "분해능 500ns."],
           ["내부 1.1V 밴드갭", "외부 분압 기준",
            "부품 추가 없이 전원·온도 변동에 둔감한 기준을 얻는다."],
           ["SSD1306 OLED (I2C)", "16x2 문자 LCD",
            "핀 2개로 등록 절차 안내가 가능. 기존 드라이버를 그대로 재사용."]],
          y=1.55, fs=13)

    # ---------------- 8. 핀 배정과 회로도 ----------------
    s = new_slide(prs, "핀 배정과 회로 구성", "요강 4-가-2 · 4-가-4", num())
    picture(s, "schematic.png", 0.35, 1.25, h=5.35)
    tf = textbox(s, 9.6, 1.35, 3.5, 5.2)
    para(tf, "사용 핀 10개", 17, True, ACCENT, 8, first=True)
    for t in ("PD2~PD5  버튼 4개",
              "PD7 (AIN1)  피에조 — 시각",
              "PC0 (ADC0)  피에조 — 진폭",
              "PC4/PC5  OLED I2C",
              "PB1  액추에이터",
              "PD0/PD1  UART"):
        para(tf, "· " + t, 13, False, INK, 4)
    para(tf, "핵심 배선", 15, True, ACCENT, 6)
    for t in ("피에조 노드에서 선을 두 가닥 뽑아",
              "PD7 과 PC0 에 각각 연결한다.",
              "ACME=0 이어야 비교기와 ADC 를",
              "동시에 쓸 수 있기 때문이다.",
              "",
              "1MΩ 블리드 저항이 없으면 압전",
              "전하가 빠지지 못해 두 번째",
              "노크부터 문턱을 넘지 못한다."):
        para(tf, t, 12.5, False, INK if "1MΩ" not in t else WARN, 2)

    # ---------------- 9. 프로그램 흐름 ----------------
    s = new_slide(prs, "프로그램 흐름 — 인증 상태 기계", "요강 4-가-2", num())
    picture(s, "fig2_flow.png", 0.62, 1.25, w=12.1)

    # ---------------- 10. 핵심 1: 하드웨어 캡처 ----------------
    s = new_slide(prs, "설계 1 — 왜 ADC 폴링이 아니라 하드웨어 캡처인가",
                  "난이도 · 레지스터 직접 제어", num(),
                  "리듬 인증은 간격의 재현성이 전부이므로 측정 지터를 없애야 한다")
    code_box(s, [
        "ACSR = (1 << ACBG) | (1 << ACIC);",
        "  ACBG=1 : 내부 1.1V 밴드갭을 양극 입력으로",
        "  ACIC=1 : 비교기 출력을 Timer1 입력 캡처에 직결",
        "",
        "TCCR1A = 0;",
        "TCCR1B = (1 << ICNC1) | (1 << CS11);",
        "  ICNC1=1 : 노이즈 캔슬러 (4표본 연속 일치)",
        "  ICES1=0 : 하강 에지",
        "            평상시 ACO=1, 노크 시 0 으로 하강",
        "  CS11=1  : 분주 /8 -> 500ns 분해능",
        "",
        "TIMSK1 = (1 << ICIE1) | (1 << TOIE1);",
    ], x=0.75, y=1.65, w=6.0, h=3.55, title="knock.c — knock_init()")
    tf = textbox(s, 7.05, 1.65, 5.55, 3.6)
    para(tf, "ADC 폴링의 문제", 16, True, WARN, 6, first=True)
    for t in ("검출 시각이 샘플링 주기만큼 양자화된다",
              "인터럽트 지연이 그대로 측정값에 섞인다",
              "OLED·EEPROM 접근 중에는 표본이 빈다"):
        para(tf, "· " + t, 13.5, False, INK, 4)
    para(tf, "입력 캡처의 이점", 16, True, OK, 6)
    for t in ("ICR1 래치가 하드웨어에서 일어난다",
              "ISR 이 늦게 실행되어도 시각은 흔들리지 않는다",
              "ICNC1 의 4클럭 지연은 모든 노크에 동일하게",
              "  적용되는 상수라 간격에는 영향이 없다"):
        para(tf, "· " + t, 13.5, False, INK, 4)
    note_box(s, [
        "기존 PEDD 프로젝트에서 검증한 구조를 계승했다. 다만 방전 방향이 "
        "반대라 에지 방향이 다르다 — pedd.c 는 상승, knock.c 는 하강.",
    ], y=5.55, h=0.85,
        fill=RGBColor(0xF5, 0xF3, 0xFF), line=ACCENT, color=ACCENT)

    # ---------------- 11. 핵심 2: 링잉 불응기 ----------------
    s = new_slide(prs, "설계 2 — 압전 링잉을 어떻게 걸러내는가",
                  "설계 및 실험 과정", num(),
                  "한 번의 타격에 소자와 부착면이 수 ms 동안 공진한다")
    bullets(s, [
        ("증상", 0, True),
        ("노크 1회가 이벤트 3~5회로 잡혀 간격 벡터가 통째로 무너진다", 1, False),
        ("대책 (2중)", 0, True),
        ("하드웨어 — ICNC1 노이즈 캔슬러가 문턱 근처의 비교기 채터링을 "
         "4표본 일치 조건으로 거른다", 1, False),
        ("소프트웨어 — 첫 검출 후 50ms 동안의 추가 에지는 같은 노크의 "
         "잔향으로 보고 버린다 (불응기)", 1, False),
        ("불응기 값의 근거", 0, True),
        ("50ms 는 초당 20회까지 허용하므로 사람이 두드리는 속도에 충분하다. "
         "최종값은 실험 1에서 UART 로그의 실제 간격 분포를 보고 확정한다.", 1,
         False),
    ], y=1.75, size=16)
    code_box(s, [
        "if ((uint32_t)(now - g_last_ts) < BLANK_TICKS) {",
        "    return;          /* 잔향 — 버린다 */",
        "}",
        "g_last_ts = now;     /* 받아들인 에지만 기준을 갱신 */",
    ], x=6.9, y=4.15, w=5.7, h=1.25, title="knock.c — TIMER1_CAPT_vect")
    note_box(s, [
        "설계 주의 — 버린 에지로는 기준 시각을 갱신하지 않는다. 갱신하면 "
        "잔향이 이어지는 동안 불응기가 무한히 연장되어 다음 노크를 놓친다.",
    ], y=5.65, h=0.9)

    # ---------------- 12. 핵심 3: 템포 정규화 ----------------
    s = new_slide(prs, "설계 3 — 템포 정규화 (이게 없으면 본인도 못 연다)",
                  "난이도 · 알고리즘", num(),
                  "절대 간격으로 비교하면 조금만 빨리 쳐도 전부 거부된다")
    table(s,
          ["입력", "간격 벡터 (ms)", "정규화 지문", "판정"],
          [["등록한 리듬", "[200, 400, 200]", "[250, 500, 250]", "*기준"],
           ["1.5배 느리게", "[300, 600, 300]", "[250, 500, 250]", "*통과"],
           ["2배 빠르게", "[100, 200, 100]", "[250, 500, 250]", "*통과"],
           ["다른 리듬", "[200, 200, 400]", "[250, 250, 500]", "거부 (d²=125,000)"]],
          y=1.85, fs=14)
    code_box(s, [
        "/* 전 구간 32비트 정수. float 미사용 */",
        "while (total > KNOCKFP_SHIFT_LIMIT) {   /* 오버플로 방지 */",
        "    total = 0;",
        "    for (k = 0; k < CLASSIFY_CHANNELS; k++) {",
        "        g[k] >>= 1;      /* 동일 배율 -> 비율 보존 */",
        "        total += g[k];",
        "    }",
        "}",
        "fp->n[k] = (uint16_t)((g[k] * CLASSIFY_NORM_SUM) / total);",
    ], x=0.75, y=4.15, w=7.4, h=2.35, title="knockfp.c — knockfp_make()")
    tf = textbox(s, 8.4, 4.25, 4.2, 2.2)
    para(tf, "부동소수점을 쓰지 않는 이유", 14, True, ACCENT, 6, first=True)
    # 줄바꿈은 word_wrap 에 맡긴다. 손으로 자르면 이어지는 줄에도 글머리표가
    # 붙어 별개 항목처럼 읽힌다.
    for t in ("AVR 은 FPU 가 없어 소프트 FP 라이브러리가 링크된다 (1.5~3KB)",
              "정수 나눗셈 3회로 끝나므로 8비트 MCU 에서도 가볍다",
              "판정은 기존 classify_match() 를 한 줄도 고치지 않고 재사용"):
        para(tf, "· " + t, 12.5, False, INK, 5)

    # ---------------- 13. 핵심 4: 임계값 자동 유도 ----------------
    s = new_slide(prs, "설계 4 — 임계값을 손으로 정하지 않는다",
                  "완성도 · 최적화", num(),
                  "사용자 본인의 재현성에서 허용 반경을 유도한다")
    bullets(s, [
        ("방법", 0, True),
        ("등록 시 같은 리듬을 5회 반복 입력받는다", 1, False),
        ("평균 = 중심점, (표본들이 중심점에서 벗어난 최대 제곱거리) × 2 "
         "= 임계값", 1, False),
        ("효과", 0, True),
        ("리듬이 일정한 사람은 좁게, 들쭉날쭉한 사람은 넓게 잡힌다 "
         "— 오거부(FRR)를 줄이면서도 필요 이상으로 헐거워지지 않는다", 1, False),
        ("흩어짐이 상한(20,000)을 넘으면 등록 자체를 거부한다. 무리하게 "
         "넓혀 저장하면 타인도 함께 통과하기 때문이다", 1, False),
    ], y=1.75, size=16)
    note_box(s, [
        "개발 중 단위 테스트가 잡아낸 결함 — 임계값 상한이 60,000 이었을 때, "
        "(250,500,250) 과 (333,333,333) 처럼 명백히 다른 리듬의 제곱거리"
        "(41,667)가 상한 안에 들어와 통과했다.",
        "지문의 세 성분 합이 1,000 이므로 임계값의 제곱근이 곧 허용 반경이다. "
        "20,000 (반경 141 ≈ 성분당 8%) 로 낮추고 회귀 테스트를 추가했다.",
        "최종값은 실험 3·4 의 FRR/FAR 곡선을 보고 확정한다.",
    ], y=4.55, h=1.85,
        fill=RGBColor(0xF5, 0xF3, 0xFF), line=ACCENT, color=ACCENT)

    # ---------------- 14. 핵심 5: 보안 예외 처리 ----------------
    s = new_slide(prs, "설계 5 — 예외적 경우에 대한 대비", "완성도", num(),
                  "잠금장치는 정상 동작보다 비정상 상황에서의 거동이 중요하다")
    table(s,
          ["공격 / 상황", "대비"],
          [["*틀릴 때마다 전원을 뽑아 실패 카운터 초기화",
            "*카운터를 EEPROM 에 두고, 평가하기 전에 먼저 증가시킨다"],
           ["카운터 기록 중 전원 차단으로 값 손상",
            "값과 보수를 함께 저장. 어긋나면 최대 실패로 간주 (fail-closed)"],
           ["대기 화면에서 아무나 등록을 덮어씀",
            "재등록은 인증 성공 직후에만 허용 (미등록 상태만 예외)"],
           ["응답 시간 차이로 순서를 한 자리씩 추측",
            "조기 반환 없이 항상 전 슬롯·전 자릿수를 비교"],
           ["잠금이 영구화되어 장치가 벽돌이 됨",
            "5회 실패 → 30초 대기. 대기를 채우면 카운터가 0 으로 복귀"],
           ["공장 출하 EEPROM(전 바이트 0xFF)",
            "손상이 아닌 미사용으로 구분 — 새 칩이 잠금 화면부터 뜨지 않게"]],
          y=1.85, fs=13)

    # ---------------- 15. 소프트웨어 구조 ----------------
    s = new_slide(prs, "소프트웨어 구조와 재사용", "난이도 · 하드웨어/SW 배분",
                  num())
    table(s,
          ["모듈", "상태", "역할"],
          [["classify.c / i2c.c / ssd1306.c / uart.c", "무수정 재사용",
            "정수 분류기, TWI 마스터, OLED, UART"],
           ["*knock.c", "*신규 (pedd.c 계승)",
            "*비교기 + Timer1 캡처로 노크 시각·진폭 측정"],
           ["*knockfp.c", "*신규",
            "*템포 정규화 지문. 하드웨어 비의존 — PC 단위 테스트 대상"],
           ["keypad.c", "신규 (button.c 확장)", "4키 디바운스, 짧게/길게"],
           ["timebase.c", "신규", "Timer0 1ms 시각 + Idle 슬립"],
           ["*authstore.c", "*신규 (store.c 계승)",
            "*등록 정보 + 비휘발성 실패 카운터"]],
          y=1.55, fs=13)
    note_box(s, [
        "검증 — avr-gcc 로 -Wall -Wextra -Werror 빌드 경고 0. "
        "knockfp / classify 는 avr-gdb 내장 AVR 시뮬레이터에서 실제로 실행해 "
        "26개 검사를 통과시켰다 (tools/run_tests.sh).",
        "PC 용 C 컴파일러가 없는 환경이라 테스트도 ATmega328P 코드로 빌드해 "
        "시뮬레이터 위에서 돌린다.",
    ], y=5.35, h=1.25,
        fill=RGBColor(0xEC, 0xFD, 0xF5), line=OK, color=OK)

    # ---------------- 16. 실험 계획 ----------------
    s = new_slide(prs, "실험 계획", "요강 4-가-2 · 4-가-3", num())
    table(s,
          ["", "목적", "방법", "판정 기준"],
          [["1", "피에조 특성 · 파라미터 확정",
            "세기를 바꿔가며 ADC 값과 링잉 파형 기록",
            "불응기(ms)와 진폭 게이트 확정"],
           ["2", "1단계 단독 검증", "정답/오답 순서 각각 입력",
            "정답만 통과, 오답은 전부 거부"],
           ["3", "리듬 재현성", "같은 사용자가 동일 리듬 30회 이상 반복",
            "제곱거리 분포에서 FRR 산출"],
           ["*4", "*2FA 효과 실증 (핵심)",
            "*순서를 알려준 제3자 3명이 소리를 듣고 모방, 각 20회",
            "*FAR 산출 — 순서를 알아도 거부되는 비율"],
           ["5", "예외 상황 대비 확인",
            "임계값 경계 반복, 인증 중 전원 차단, 재등록 시도",
            "재시도 제한·잠금·안내가 설계대로 동작"]],
          y=1.55, fs=13)
    note_box(s, [
        "데이터는 전부 UART CSV 로 자동 수집된다 — "
        "seq,mode,pin_user,knock_user,d2,thr,n0..n2,g0..g2ms,a0..a3,result",
        "실험 3·4 의 FRR/FAR 은 result 열을 세면 그대로 나오고, "
        "d2 열로 임계값 곡선(ROC)을 그린다.",
    ], y=5.55, h=1.15)

    # ---------------- 17. 실험 3 결과 (자리) ----------------
    s = new_slide(prs, "실험 결과 3 — 리듬 재현성", "실측 후 작성", num())
    todo_box(s, [
        "[측정 후 이 상자를 교체]",
        "",
        "· 넣을 것 1 — 동일 사용자 30회 반복의 제곱거리 히스토그램",
        "· 넣을 것 2 — 정규화 성분 n0/n1/n2 의 평균과 변동계수(CV) 표",
        "· 넣을 것 3 — 임계값을 바꿔가며 그린 FRR 곡선",
        "",
        "· 서술할 것 — 자동 유도된 임계값이 실제 분포와 얼마나 맞았는지,",
        "  맞지 않았다면 THRESHOLD_MARGIN 을 어떻게 조정했는지",
        "",
        "데이터 출처: UART 로그의 mode=AUTH 행",
    ], y=1.85, h=4.6)

    # ---------------- 18. 실험 4 결과 (자리) ----------------
    s = new_slide(prs, "실험 결과 4 — 타인 모사 시도 (2FA 효과 실증)",
                  "실측 후 작성 · 핵심 슬라이드", num())
    todo_box(s, [
        "[측정 후 이 상자를 교체 — 이 작품의 주장을 증명하는 유일한 장이다]",
        "",
        "· 넣을 것 1 — 조건별 통과율 막대그래프",
        "    (a) 본인          (b) 순서만 아는 타인",
        "    (c) 리듬만 흉내낸 타인   (d) 둘 다 시도한 타인",
        "· 넣을 것 2 — FAR / FRR 표 (시도 횟수와 함께)",
        "· 넣을 것 3 — 본인과 타인의 제곱거리 분포 산점도",
        "",
        "· 서술할 것 — '순서가 노출되어도 뚫리지 않는다'가 몇 %의 근거로",
        "  뒷받침되는지. 뚫린 사례가 있다면 그 조건도 함께 밝힐 것",
    ], y=1.85, h=4.6)

    # ---------------- 19. 메모리 사용량 ----------------
    s = new_slide(prs, "메모리 사용량", "요강 4-가-6 · 경제성", num())
    table(s,
          ["구분", "사용량", "용량", "비율"],
          [["*Flash (프로그램)", "*8,908 B", "*32,768 B", "*27.2 %"],
           ["*SRAM (데이터)", "*110 B", "*2,048 B", "*5.4 %"],
           ["EEPROM", "40 B", "1,024 B", "3.9 %"]],
          y=1.6, fs=15, h=1.8)
    tf = textbox(s, 0.75, 3.55, 11.9, 0.6)
    para(tf, "절감 근거", 16, True, ACCENT, 4, first=True)
    for t in ("부동소수점 미사용 — 소프트 FP 라이브러리(1.5~3KB)가 링크되지 않음",
              "OLED 프레임버퍼 미사용 — 페이지 주소 모드로 직접 기록 "
              "(1,024B = SRAM 절반을 절약)",
              "화면 문구를 전부 PSTR() 로 Flash 에 상주 — SRAM 복사 회피"):
        para(tf, "· " + t, 13.5, False, INK, 3)
    todo_box(s, [
        "[제출 전 교체] Microchip Studio 빌드 출력창 캡처를 여기에 붙일 것.",
        "요강 4-가-6 이 '화면 캡처'를 명시하므로 위 표만으로는 부족하다.",
        "Studio 의 Output 창 하단에 Program Memory / Data Memory Usage 가 나온다.",
    ], y=5.05, h=1.35)

    # ---------------- 20. 부품 가격표 ----------------
    s = new_slide(prs, "부품 가격표", "요강 4-가-7 · 경제성", num())
    table(s,
          ["품목", "사양", "수량", "단가", "금액", "비고"],
          [["ATmega328P", "28-pin PDIP", "1", "", "", "요강 허용 MCU"],
           ["압전 디스크", "피에조 진동 센서", "1", "", "", "노크 검출 핵심"],
           ["택트 스위치", "4핀", "4", "", "", "순서 입력"],
           ["I2C OLED", "0.96\" SSD1306", "1", "", "", "상태 표시"],
           ["저항", "1MΩ·1kΩ·330Ω·10kΩ", "각 1", "", "", "블리드·보호·풀업"],
           ["다이오드", "1N4148", "2", "", "", "입력 클램프"],
           ["수정 진동자 + C", "16MHz + 22pF×2 등", "1식", "", "",
            "보드 사용 시 불필요"],
           ["*합계", "", "", "", "*(기입)", "*브레드보드 별도"]],
          y=1.45, fs=12.5)
    note_box(s, [
        "작성 지침 — 요강 3-라(경제성)는 시스템 전체 부품 원가를 본다. "
        "기보유품도 시장가로 함께 적고, 단가는 실제 구매 영수증 기준으로 채울 것.",
        "개발보드 대신 ATmega328P 단품 구성으로 가면 보드·크리스탈이 빠져 "
        "총원가가 더 내려가고, 요강 2-가-3 의 'Custom 보드' 가산도 노릴 수 있다.",
    ], y=5.9, h=1.3)

    # ---------------- 21. 해결하지 못한 부분 ----------------
    s = new_slide(prs, "계획했으나 해결하지 못한 부분", "요강 4-가-5", num(),
                  "감점 항목이 아니라 요강이 명시적으로 요구하는 제출 항목이다")
    table(s,
          ["항목", "현재 상태", "원인 / 향후 계획"],
          [["노크 위치 분류 (피에조 2개)",
            "미구현",
            "진폭비로 타격 구역을 나누면 버튼 없이 '보이지 않는 키패드'가 "
            "된다. 도달 시간차(TDOA)는 328P 의 비교기가 1개뿐이라 불가."],
           ["Power-down 저전력",
            "Idle 모드까지만",
            "Power-down 에서는 비교기가 정지해 노크를 감지할 수 없다. "
            "버튼 기상 후 노크를 받는 2단 구조가 필요."],
           ["다중 사용자",
            "슬롯 3개 구현, 검증 부족",
            "EEPROM 여유는 충분하나 등록 UI 와 사용자 간 오인식 검증이 남음."],
           ["임계값 상한의 실측 근거",
            "설계값(20,000)",
            "실험 3·4 데이터로 확정 예정. 현재 값은 기하학적 계산에 근거."],
           ["가변 문턱 (PWM DAC)",
            "미구현",
            "Timer2 PWM + RC 로 1핀 DAC 를 만들면 문턱을 코드로 조절 가능. "
            "현재는 ADC 진폭 게이트로 대체."]],
          y=1.85, fs=12.5)

    # ---------------- 22. 결론 ----------------
    s = new_slide(prs, "결론 및 기대효과", None, num())
    bullets(s, [
        ("성과", 0, True),
        ("추가 부품 1개로 '지식 + 행동' 이중 인증을 구현했다. "
         "지문 모듈 대비 원가가 압도적으로 낮다.", 1, False),
        ("Arduino 라이브러리 없이 비교기·타이머 캡처·ADC·EEPROM·I2C·"
         "슬립을 전부 레지스터로 직접 제어했다.", 1, False),
        ("측정 정밀도를 하드웨어(입력 캡처)에, 판정 로직을 소프트웨어"
         "(정수 분류기)에 배분해 8비트 MCU 에서 Flash 27% 로 동작한다.", 1,
         False),
        ("단순한 아이디어 제시에 그치지 않고 타인 모사 실험으로 2FA 효과를 "
         "정량 증명한다.", 1, False),
        ("확장", 0, True),
        ("피에조 2개로 타격 위치까지 분류하면 버튼이 사라지고 표면 전체가 "
         "입력 장치가 된다 — 외부에 드러나는 조작부가 없는 잠금장치.", 1, False),
    ], y=1.55, size=16)
    note_box(s, [
        "이 작품의 한 문장 — '순서를 안다고 해도, 그 순서를 두드리는 리듬까지 "
        "똑같이 재현하기는 어렵다.'",
    ], y=6.0, h=0.85,
        fill=RGBColor(0xF5, 0xF3, 0xFF), line=ACCENT, color=ACCENT)

    outdir = os.path.join(ROOT, "제출물")
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    path = os.path.join(outdir, "가_예선보고서_초안.pptx")
    prs.save(path)
    print("생성: %s (%d 슬라이드, %d bytes)"
          % (path, len(prs.slides.__iter__.__self__._sldIdLst),
             os.path.getsize(path)))
    return path


if __name__ == "__main__":
    build()
