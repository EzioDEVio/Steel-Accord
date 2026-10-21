#!/bin/sh
# Boot the engine in a clean folder under Wine/Xvfb (development harness, B2 gate).
# usage: tools/run_clean.sh <seconds> [game args...]
# The folder build/clean contains ONLY: generalszh.exe, the d3dx8d shim, and our archives/data.
# Outputs in build/clean: files.log (every file the engine tried to open), DebugLogFile.txt,
# screenshot.png (virtual display at the end of the run).
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
C="$ROOT/build/clean"; SECS="${1:-60}"; shift || true
ENGINE_EXE="${ENGINE_EXE:-/home/claude/engine/build/mingw-w64-i686/GeneralsMD/generalszh.exe}"
mkdir -p "$C"
cp "$ENGINE_EXE" "$C/generalszh.exe"
cp "$ROOT/tools/winshim/d3dx8d.dll" "$C/"
python3 -c "import sys; sys.path.insert(0, \"$ROOT/tools\"); from pzlib import big; big.pack(\"$ROOT/content/base\", \"$C/SABase.big\")"
rm -f "$C/files.log" "$C/DebugLogFile.txt" "$C/screenshot.png"
pgrep -x Xvfb >/dev/null || (Xvfb :99 -screen 0 1280x1024x24 >/dev/null 2>&1 &) ; sleep 1
export WINEDEBUG=-all DISPLAY=:99 WINEPREFIX=/root/.wine32
export PZH_FILE_ACCESS_LOG="Z:$(echo "$C/files.log" | tr / '\\\\')"
cd "$C"
wine generalszh.exe "$@" > wine.out 2>&1 &
PID=$!
i=0; while [ $i -lt "$SECS" ] && kill -0 $PID 2>/dev/null; do sleep 1; i=$((i+1)); done
import -window root "$C/screenshot.png" 2>/dev/null
if kill -0 $PID 2>/dev/null; then echo "still running after ${SECS}s (killed)"; wineserver -k 2>/dev/null; else wait $PID; echo "exited with $? after ${i}s"; fi
echo "--- files opened: $(grep -c '^[LA] ' files.log 2>/dev/null || echo 0), missing: $(grep -c '^- ' files.log 2>/dev/null || echo 0)"
tail -n 15 DebugLogFile.txt 2>/dev/null
