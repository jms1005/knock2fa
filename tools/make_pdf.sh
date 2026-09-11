#!/bin/sh
# 회로도 SVG -> 제출용 A3 가로 1페이지 PDF
#
# Chrome 헤드리스 인쇄를 쓴다. 한글이 섞인 경로에서 file:// URL 이 깨지므로
# 임시 ASCII 경로로 복사한 뒤 변환하고 결과만 되가져온다.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="${TMPDIR:-/tmp}/knock2fa_pdf"

python "$ROOT/tools/make_schematic.py"

rm -rf "$TMP"; mkdir -p "$TMP"
cp "$ROOT/figures/schematic.svg" "$ROOT/figures/schematic_print.html" "$TMP/"
WINTMP=$(cd "$TMP" && pwd -W 2>/dev/null || echo "$TMP")

"$CHROME" --headless --disable-gpu --no-sandbox \
  --print-to-pdf="$TMP/schematic.pdf" --no-pdf-header-footer \
  "file:///$WINTMP/schematic_print.html"

mkdir -p "$ROOT/제출물"
cp "$TMP/schematic.pdf" "$ROOT/제출물/나_회로도.pdf"
echo "생성: 제출물/나_회로도.pdf"
