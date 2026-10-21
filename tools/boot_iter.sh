#!/bin/sh
# One clean-boot iteration: run, then summarise what the engine looked for and where it stopped.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; C="$ROOT/build/clean"
python3 "$ROOT/tools/gen_base_stubs.py" >/dev/null
"$ROOT/tools/run_clean.sh" "${1:-40}" -win -ignoreAsserts 2>&1 | grep -E "still running|exited"
echo "--- last init steps:"; grep "PZH initSubsystem" "$C/DebugLogFile.txt" | tail -3
echo "--- tail of debug log:"; grep -v "PZH initSubsystem\|MiniDumper" "$C/DebugLogFile.txt" | tail -${2:-8}
echo "--- not found (unique, last 15):"; grep "^[?-] " "$C/files.log" | awk '!s[$0]++' | tail -15
D="/root/.wine32/drive_c/users/root/Documents/Command and Conquer Generals Zero Hour Data"
[ -f "$D/ReleaseCrashInfo.txt" ] && find "$D/ReleaseCrashInfo.txt" -newer "$C/generalszh.exe" | grep -q . && { echo "--- crash:"; sed -n 1,4p "$D/ReleaseCrashInfo.txt"; }
