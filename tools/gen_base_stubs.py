#!/usr/bin/env python3
"""Create Steel Accord base-data INI files the engine requires at boot (B2 standalone).

INI::loadFileDirectory defaults to LoadFlags_ExpectFileFound: every subsystem path must
resolve to at least one file or the engine throws during init (observed in the clean-folder
boot, 2026-10-21). This writes a minimal, original file for each required path that we have
not yet authored by hand. Hand-authored files are never overwritten.
"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "content", "base", "Data", "INI")
PATHS = """AIData Armor CommandMap Crate DamageFX Default/AIData Default/Crate Default/FXList Default/GameData
Default/Multiplayer Default/Object Default/ObjectCreationList Default/PlayerTemplate Default/Roads Default/Science
Default/SpecialPower Default/Terrain Default/Upgrade FXList GameData Locomotor Multiplayer Object ObjectCreationList
PlayerTemplate Rank Roads Science SpecialPower Terrain Upgrade Weapon AudioSettings Campaign ChallengeMode
CommandButton CommandSet ControlBarResizer ControlBarScheme Credits Default/CommandButton Default/ControlBarScheme
Default/Music Default/ShellMenuScheme Default/SoundEffects Default/Speech Default/Video Default/Voice Default/Water
Default/Weather Eva GameLOD GameLODPresets InGameUI MiscAudio Mouse Music ParticleSystem ShellMenuScheme
SoundEffects Speech Video Voice Water Weather Webpages WindowTransitions DrawGroupInfo Animation2D""".split()
HEADER = ";==============================================================================\n; Steel Accord - base data (original). {p}\n; Minimal file: engine requires one file per subsystem path; defaults come from engine code.\n;==============================================================================\n"


def main():
    made = 0
    for p in PATHS:
        f = os.path.join(BASE, p.replace("/", os.sep) + ".ini")
        if os.path.exists(f):
            continue
        os.makedirs(os.path.dirname(f), exist_ok=True)
        open(f, "w").write(HEADER.format(p=p))
        made += 1
    print(f"base stubs: {made} created, {len(PATHS) - made} already authored")


if __name__ == "__main__":
    main()
