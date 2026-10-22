# Aircraft asset manifest (U.S. aircraft pack)

Generated from `content/manifest/aircraft.json` by hand-off of `tools/import_aircraft.py`. Source archives are unchanged; intact originals are kept in `art_source/us_aircraft/<id>/` with SHA-256 hashes in the JSON.

**Representation:** every aircraft is a **sprite** in-game: the supplied top-down art lies on a horizontal, lit, shadow-casting quad. The three-quarter view is used as the portrait. **None of these is a 3D model.**

**Shipping status: DEV ONLY.** The images are AI-generated (supplied by the client, made with ChatGPT image generation) and depict **real aircraft designs**, real names (manufacturer trademarks) and U.S. national insignia. They need a rights review before any public release. Future factions should use fictional designs (see `docs/ASSET_GENERATION_README.md`).

Source archives: `US_Aircraft_Game_Assets.zip` (sha256 b827015…5c1) and `US_Aircraft_Game_Assets_Expanded.zip` (sha256 922c3a5…002).

| ID | Source name | In-game use | Status | Sprite scale | Portrait from | Missing / corrupt in the packs |
|---|---|---|---|---|---|---|
| `f16` | F-16 Fighting Falcon | unit:jet_multirole | sprite+icon generated | 15.1 m (43 px/m) | front_three_quarter | - |
| `fa18` | F-A-18 Hornet | unit:jet_strike | sprite+icon generated | 17.1 m (38 px/m) | front_three_quarter | - |
| `f22` | F-22 Raptor | unit:jet_air_superiority | sprite+icon generated | 18.9 m (31 px/m) | front_three_quarter | - |
| `a10` | A-10 Thunderbolt II Warthog | unit:jet_ground_attack | sprite+icon generated | 16.3 m (38 px/m) | side_profile | A-10_Thunderbolt_II_Warthog_front_three_quarter.png |
| `ah64` | AH-64 Apache | unit:heli_attack | sprite+icon generated | 17.7 m (43 px/m) | front_three_quarter | - |
| `uh60` | UH-60 Black Hawk | unit:heli_transport | sprite+icon generated | 19.8 m (32 px/m) | front_three_quarter | - |
| `ch47` | CH-47 Chinook | unit:heli_heavy_transport | sprite+icon generated | 30.1 m (20 px/m) | front_three_quarter | - |
| `b52` | B-52 Stratofortress | support_power:carpet_bombing | sprite+icon generated | 48.5 m (12 px/m) | front_three_quarter | - |
| `b1` | B-1 Lancer | support_power:supersonic_strike | sprite+icon generated | 44.5 m (13 px/m) | front_three_quarter | - |
| `b2` | B-2 Spirit | support_power:stealth_precision_strike | sprite+icon generated | 21.0 m (21 px/m) | front_three_quarter | - |
| `sr71` | SR-71 Blackbird | support_power:recon_overflight | sprite+icon generated | 32.7 m (20 px/m) | front_three_quarter | - |

Pack issues found on import:
- The expanded README says "Fourteen aircraft" but the pack lists and contains eleven.
- Three PNGs in the expanded zip are truncated (corrupt): A-10, B-2 and F-22 `front_three_quarter`. B-2 and F-22 were taken intact from the first zip. The A-10 has no intact copy, so its portrait uses the side profile. **Please regenerate `A-10_Thunderbolt_II_Warthog_front_three_quarter.png`.**
- The supplied 768×512 overhead crops cut off the tails of longer airframes and include fragments of neighbouring views. The importer re-cuts each overhead view from the 4-view contact sheet as one connected silhouette.
- Nose direction differs between sheets (up / down / left). It's recorded per aircraft (`source_nose_direction`) and normalised to nose-up.

Gameplay values for all aircraft are **PROVISIONAL** (`godot/scripts/unit_defs.gd`).
