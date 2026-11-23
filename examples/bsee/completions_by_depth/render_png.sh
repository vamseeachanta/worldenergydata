#!/usr/bin/env bash
# Render each chart SVG in a folder to a PNG at twice its size with headless
# Chrome. Usage: render_png.sh [folder]   (default: output beside this script)
set -euo pipefail
dir="$(cd "${1:-$(dirname "$0")/output}" && pwd)"
for svg in "$dir"/*.svg; do
  height="$(sed -n 's/.* width="960" height="\([0-9]*\)".*/\1/p' "$svg" | head -1)"
  google-chrome --headless=new --hide-scrollbars --force-device-scale-factor=2 \
    --window-size="960,${height}" --screenshot="${svg%.svg}.png" "file://${svg}" \
    >/dev/null 2>&1
  echo "${svg##*/} -> $(basename "${svg%.svg}.png")"
done
