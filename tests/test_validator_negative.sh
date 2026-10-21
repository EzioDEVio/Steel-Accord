#!/bin/sh
# Negative tests: each mutation must make validate_content.py FAIL. usage: tests/test_validator_negative.sh <engine>
ENGINE="$1"; set -u
SRC="$(cd "$(dirname "$0")/.." && pwd)"
fail=0
run() { # $1 description, $2 file, $3 sed expr
  T=$(mktemp -d); cp -r "$SRC/tools" "$SRC/content" "$SRC/maps" "$T/"
  sed -i "$3" "$T/$2"
  if python3 "$T/tools/validate_content.py" --engine "$ENGINE" --skip-manifest >/dev/null 2>&1; then echo "MISSED: $1"; fail=1; else echo "caught: $1"; fi
  rm -rf "$T"
}
run "misspelled field"        content/dev/Data/INI/Object/PZDev_Kestrel.ini 's/MaxHealth /MaxHelth /'
run "unknown module"          content/dev/Data/INI/Object/PZDev_Kestrel.ini 's/= ActiveBody/= ActiveBodyX/'
run "dangling weapon ref"     content/dev/Data/INI/Object/PZDev_Kestrel.ini 's/PRIMARY PZDevKestrelChainGun/PRIMARY NoSuchGun/'
run "bad KindOf"              content/dev/Data/INI/Object/PZDev_Kestrel.ini 's/SCORE/SCOREZ/'
run "missing model file"      content/dev/Data/INI/Object/PZDev_Kestrel.ini 's/Model = PZKESTRELHK/Model = PZNOPE/'
run "missing string"          maps/PZ_TestRange/map.str 's/OBJECT:PZDevKestrel$/OBJECT:PZDevKestrelZZ/'
run "bad damage type"         content/dev/Data/INI/Weapon/PZDev_Weapons.ini 's/SMALL_ARMS/SMALLARMS/'
run "bad image coords"        content/dev/Data/INI/MappedImages/HandCreated/PZDev_Images.ini 's/Right:251/Right:300/'
run "unlisted base cmdset"    maps/PZ_TestRange/map.ini 's/ChinaCommandCenterCommandSet/GLACommandCenterCommandSet/'
run "unterminated block"      content/dev/Data/INI/Armor/PZDev_Armor.ini '$d'
T=$(mktemp -d); cp -r "$SRC/tools" "$SRC/content" "$SRC/maps" "$T/"
if python3 "$T/tools/validate_content.py" --engine "$ENGINE" --skip-manifest >/dev/null 2>&1; then echo "baseline (skip-manifest) passes"; else echo "BASELINE FAILS"; fail=1; fi
printf x >> "$T/content/dev/Data/INI/Armor/PZDev_Armor.ini"
if python3 "$T/tools/validate_content.py" --engine "$ENGINE" >/dev/null 2>&1; then echo "MISSED: manifest hash"; fail=1; else echo "caught: manifest hash mismatch"; fi
rm -rf "$T"
exit $fail
