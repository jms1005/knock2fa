# -*- coding: utf-8 -*-
"""
pack_submission.py — 제출물 폴더를 한 번에 정리한다.

운영설명 PDF 「4. 예선 제출물」의 4개 항목에 1:1 대응한다.

  가. 발표 형식의 보고서 (PPT)  -> 가_예선보고서_초안.pptx
  나. 회로도 (PDF)              -> 나_회로도.pdf
  다. Source Code               -> 다_소스코드.zip
  라. 동작 동영상               -> (직접 촬영해 넣을 것)

실행:  python tools/pack_submission.py
"""

import io
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "제출물")

# 소스 zip 에 담을 것. 빌드 산출물(build/)과 그림 중간물은 넣지 않는다.
SRC_DIRS = ["firmware", "tests", "tools"]
SRC_FILES = ["README.md"]
SKIP_EXT = (".pyc",)
SKIP_DIRS = ("__pycache__", "Debug", "Release", "build")


def pack_source():
    path = os.path.join(OUT, "다_소스코드.zip")
    n = 0
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for d in SRC_DIRS:
            base = os.path.join(ROOT, d)
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [x for x in dirnames if x not in SKIP_DIRS]
                for fn in filenames:
                    if fn.endswith(SKIP_EXT):
                        continue
                    full = os.path.join(dirpath, fn)
                    z.write(full, os.path.relpath(full, ROOT))
                    n += 1
        for fn in SRC_FILES:
            full = os.path.join(ROOT, fn)
            if os.path.exists(full):
                z.write(full, fn)
                n += 1
    return path, n


CHECKLIST = """# 예선 제출 체크리스트

운영설명 PDF 「4. 예선 제출물」 대응표. 제출 전에 하나씩 확인할 것.

| 요강 | 제출물 | 상태 |
|---|---|---|
| 가. 발표 형식의 보고서 (PPT) | `가_예선보고서_초안.pptx` | **초안 — 실측 후 완성 필요** |
| 나. 회로도 (PDF) | `나_회로도.pdf` | 완료 (A3 가로 1페이지) |
| 다. Source Code | `다_소스코드.zip` | 완료 |
| 라. 동작 동영상 | (없음) | **직접 촬영 필요** |

## PPT 에서 반드시 채워야 하는 곳 (붉은 상자)

- **슬라이드 17** 실험 3 — 리듬 재현성. 제곱거리 히스토그램, 변동계수 표, FRR 곡선
- **슬라이드 18** 실험 4 — 타인 모사. 조건별 통과율, FAR/FRR 표, 산점도
  - 이 장이 이 작품의 주장을 증명하는 유일한 장이다. 가장 공들일 것
- **슬라이드 19** 메모리 사용량 — Microchip Studio 빌드 출력창 캡처
  - 요강 4-가-6 이 "화면 캡처"를 명시한다. 표만으로는 부족하다
- **슬라이드 20** 부품 가격표 — 실제 구매 영수증 기준 단가·합계
- **표지** 팀명 / 소속 / 성명
- **회로도 표제란** 설계자 이름 (`tools/make_schematic.py` 의 "(팀명 기입)")

## 동영상에 반드시 담을 것

1. 등록 절차 — 순서 4자리 + 같은 리듬 5회 반복, EEPROM 저장 화면
2. 정상 인증 — 순서 + 리듬 → UNLOCKED
3. **순서만 아는 타인이 시도 → DENIED** (2FA 효과를 눈으로 보여주는 장면)
4. 5회 연속 실패 → LOCKOUT 화면
5. **잠금 상태에서 전원을 뽑았다 꽂아도 여전히 잠겨 있는 장면**
   (실패 카운터가 비휘발성이라는 증거. 심사에서 강한 인상을 남긴다)
6. UART 로그가 실시간으로 찍히는 터미널 화면

## 재생성 명령

```sh
sh tools/render_figures.sh    # 회로도·블록도·흐름도 SVG -> PNG
sh tools/make_pdf.sh          # 회로도 -> 제출용 A3 PDF
python tools/make_ppt.py      # 발표자료 초안
python tools/pack_submission.py   # 소스 zip + 이 체크리스트
sh tools/build_check.sh       # 펌웨어 빌드 + 메모리 사용량
sh tools/run_tests.sh         # 단위 테스트 (AVR 시뮬레이터)
```
"""


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)

    zpath, n = pack_source()
    print("생성: %s (%d개 파일, %d bytes)"
          % (zpath, n, os.path.getsize(zpath)))

    cpath = os.path.join(OUT, "제출_체크리스트.md")
    io.open(cpath, "w", encoding="utf-8").write(CHECKLIST)
    print("생성: %s" % cpath)

    print("")
    print("제출물 폴더 상태:")
    for fn in sorted(os.listdir(OUT)):
        full = os.path.join(OUT, fn)
        print("  %-28s %8d bytes" % (fn, os.path.getsize(full)))
    print("")
    print("  라. 동작 동영상               <- 직접 촬영해 넣을 것")


if __name__ == "__main__":
    main()
