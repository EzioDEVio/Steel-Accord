#!/bin/sh
# Repeat clean boots, auto-generating any missing window layout from its interface contract,
# until the engine stops asking for new .wnd files (or N iterations).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; C="$ROOT/build/clean"
CONTRACT="${CONTRACT:-/home/claude/refpatch/Patch104pZH/GameFilesEdited/Window}"
N="${1:-8}"; SECS="${2:-45}"
i=0
while [ $i -lt $N ]; do
  i=$((i+1))
  python3 "$ROOT/tools/gen_shell.py" >/dev/null; python3 "$ROOT/tools/gen_system_assets.py" >/dev/null
  "$ROOT/tools/boot_iter.sh" "$SECS" 6 > "$C/iter.txt" 2>&1
  missing=$(tr -d '\r' < "$C/files.log" | grep '^- Window' | sed 's/^- Window.//; s/[\\]/\//g' | sort -u)
  todo=""
  for m in $missing; do [ -f "$ROOT/content/base/Window/$m" ] || todo="$todo $m"; done
  echo "iteration $i: missing layouts:${todo:- none}"
  [ -z "$todo" ] && break
  avail=""; for m in $todo; do [ -f "$CONTRACT/$m" ] && avail="$avail $m" || echo "  no contract for $m"; done
  [ -z "$avail" ] && break
  python3 "$ROOT/tools/gen_autolayouts.py" "$CONTRACT" $avail
done
python3 "$ROOT/tools/gen_shell.py" >/dev/null
cat "$C/iter.txt"
