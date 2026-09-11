#!/bin/sh
# SVG 그림들을 PPT 삽입용 PNG 로 변환한다 (Chrome 헤드리스).
# 한글 경로에서 file:// URL 이 깨지므로 ASCII 임시 경로를 거친다.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="${TMPDIR:-/tmp}/knock2fa_png"

python "$ROOT/tools/make_schematic.py"
python "$ROOT/tools/make_figures.py"
python "$ROOT/tools/make_breadboard.py"
python "$ROOT/tools/make_breadboard_switches.py"
python "$ROOT/tools/make_breadboard_oled.py"
python "$ROOT/tools/make_breadboard_piezo.py"
python "$ROOT/tools/make_breadboard_actuator.py"
python "$ROOT/tools/make_switch_detail.py"
python "$ROOT/tools/make_bringup.py"
python "$ROOT/tools/make_schematic_bringup.py"

rm -rf "$TMP"; mkdir -p "$TMP"
mkdir -p "$ROOT/figures/png"
cp "$ROOT/figures/"*.svg "$TMP/"
WINTMP=$(cd "$TMP" && pwd -W 2>/dev/null || echo "$TMP")

render() {   # $1=파일명(확장자 제외)  $2=폭  $3=높이
  "$CHROME" --headless --disable-gpu --no-sandbox \
    --screenshot="$TMP/$1.png" --window-size=$2,$3 \
    --force-device-scale-factor=1.6 --default-background-color=FFFFFFFF \
    "file:///$WINTMP/$1.svg" >/dev/null 2>&1
  cp "$TMP/$1.png" "$ROOT/figures/png/$1.png"
  echo "  figures/png/$1.png"
}

echo "PNG 생성:"
render schematic  1560 1240
render fig1_block 1500 860
render fig2_flow  1500 900
render breadboard 1680 700
render breadboard_switches 1180 560
render breadboard_oled 1400 620
render breadboard_piezo 1680 700
render breadboard_actuator 1900 700
render switch_detail 1400 640
render bringup 1560 820
render schematic_bringup 1560 1240
