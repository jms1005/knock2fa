# -*- coding: utf-8 -*-
"""
make_bringup.py — 브링업(첫 전원 투입부터 전체 동작까지) 절차도 생성기

README §9 "브링업 순서 (한 번에 다 연결하지 말 것)" 를 그림 하나로 옮긴 것이다.
배선 그림(breadboard.svg)이 "무엇을 어디에 꽂는지"를 보여준다면, 이 그림은
"어떤 순서로, 각 단계에서 무엇을 확인하는지"를 보여준다. 같은 색·글꼴 규약은
make_figures.py 의 Fig 클래스를 그대로 재사용한다.

실행:  python tools/make_bringup.py
출력:  figures/bringup.svg
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_figures import Fig, INK, MUTE, ACCENT, WARN, OK  # noqa: E402

W, H = 1560, 820
STAGE_C = "#0f766e"


def stage_node(f, x, y, w, h, num, title, wire_line, check_lines, warn_lines=None):
    f.box(x, y, w, h, "#ffffff", INK, 2, 12)
    # 번호 배지
    f.add('<circle cx="%g" cy="%g" r="20" fill="%s"/>' % (x + 34, y + 34, STAGE_C))
    f.txt(x + 34, y + 40, str(num), 18, "middle", "700", "#ffffff")
    f.txt(x + 64, y + 40, title, 18, "start", "700", INK)

    cy = y + 74
    f.txt(x + 24, cy, "연결", 12, "start", "700", MUTE)
    f.txt(x + 60, cy, wire_line, 12.5, "start", "600", INK)

    cy += 30
    f.txt(x + 24, cy, "확인", 12, "start", "700", MUTE)
    first = True
    for line in check_lines:
        f.txt(x + 60 if first else x + 24, cy, line, 12, "start", "400", INK)
        cy += 20
        first = False

    if warn_lines:
        cy += 6
        for line in warn_lines:
            f.txt(x + 24, cy, line, 11.5, "start", "700", WARN)
            cy += 18


def main():
    f = Fig(W, H)

    f.txt(W / 2.0, 40, "knock2fa — 브링업 순서 (README §9)", 20, "middle", "700")
    f.txt(W / 2.0, 62,
          "한 번에 다 연결하지 말 것 — 아래 ①→⑥ 순서로 하나씩 붙이고, 각 단계를"
          " 확인한 뒤에만 다음으로 넘어간다.", 12.5, "middle", "400", MUTE)

    cols = [50, 540, 1030]
    rows = [110, 460]
    nw, nh = 460, 260

    positions = {
        1: (cols[0], rows[0]),
        2: (cols[1], rows[0]),
        3: (cols[2], rows[0]),
        4: (cols[2], rows[1]),
        5: (cols[1], rows[1]),
        6: (cols[0], rows[1]),
    }

    stage_node(
        f, positions[1][0], positions[1][1], nw, nh, 1, "보드만",
        "부품 없음 — 빌드 + 업로드만",
        ["OLED 없이도 UART(38400 8N1) 로", "헤더 줄이 나와야 한다."])

    stage_node(
        f, positions[2][0], positions[2][1], nw, nh, 2, "버튼 4개",
        "SW1~SW4 → PD2~PD5 (D2~D5)",
        ["순서 입력 화면에서 '*' 가 누른", "만큼 찍히는지 확인."],
        ["안 눌렀는데 이미 반응 있으면 →", "스위치를 90도 돌려 다시 꽂기"])

    stage_node(
        f, positions[3][0], positions[3][1], nw, nh, 3, "OLED",
        "SSD1306 → PC4/PC5 (SDA/SCL)",
        ["화면 전환이 되는지 확인."],
        ["안 나오면 → I2C 주소 0x3D 로", "(ssd1306.h) 재시도"])

    stage_node(
        f, positions[4][0], positions[4][1], nw, nh, 4, "피에조",
        "BZ1 + R3·R4 + D2·D3",
        ["진행 표시 '*' 가 노크마다", "하나씩 늘어나는지 확인."],
        ["1MΩ 블리드 저항(R4)부터 넣을 것",
         "한 번 쳤는데 여러 번 잡히면 →",
         "BLANK_TICKS(knock.c) 늘리기",
         "노크가 아예 안 잡히면 → ICES1", "(knock.c) 반전"])

    stage_node(
        f, positions[5][0], positions[5][1], nw, nh, 5, "등록 → 인증",
        "전체 흐름 (부품 추가 없음)",
        ["등록 후 순서 + 리듬으로 GRANT", "까지 뜨는지 전체 확인."])

    stage_node(
        f, positions[6][0], positions[6][1], nw, nh, 6, "액추에이터",
        "PB1 → LED 먼저, 서보는 마지막",
        ["해제 시 HIGH 로 바뀌는지 확인."],
        ["서보는 전류 소모로 보드가", "리셋될 수 있어 가장 마지막에"])

    def mid(n):
        x, y = positions[n]
        return x, y, x + nw, y + nh

    x1a, y1a, x1b, y1b = mid(1)
    x2a, y2a, x2b, y2b = mid(2)
    x3a, y3a, x3b, y3b = mid(3)
    x4a, y4a, x4b, y4b = mid(4)
    x5a, y5a, x5b, y5b = mid(5)
    x6a, y6a, x6b, y6b = mid(6)

    row0_mid = y1a + nh / 2.0
    row1_mid = y4a + nh / 2.0

    f.arrow([(x1b, row0_mid), (x2a, row0_mid)], STAGE_C)
    f.arrow([(x2b, row0_mid), (x3a, row0_mid)], STAGE_C)
    f.arrow([(x3a + nw / 2.0, y3b), (x4a + nw / 2.0, y4a)], STAGE_C)
    f.arrow([(x4a, row1_mid), (x5b, row1_mid)], STAGE_C)
    f.arrow([(x5a, row1_mid), (x6b, row1_mid)], STAGE_C)

    f.box(50, 750, 1460, 46, "#f0fdfa", STAGE_C, 1.8, 10)
    f.txt(70, 778,
          "UART 로그(38400 8N1)는 OLED가 죽어도 계속 나온다 — 각 단계에서 "
          "막히면 로그부터 확인할 것.", 12.5, "start", "700", STAGE_C)

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outdir = os.path.join(root, "figures")
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    f.save(os.path.join(outdir, "bringup.svg"))


if __name__ == "__main__":
    main()
