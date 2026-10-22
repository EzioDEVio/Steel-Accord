# Review of the client-supplied U.S. asset packs (2026-10-21)

**Scope:** every PNG and README in the eight ZIPs uploaded on 2026-10-21. The originals were left untouched. The automated check is `tools/qa_asset_packs.py`. Per-file results, with SHA-256, transparency, edge-clipping and fragment counts, are in `content/manifest/qa_us_packs_2026-10-21.json`. On top of that, every contact sheet was inspected visually.

## 1. Inventory

| ZIP | Content | PNGs | Corrupt | Notes |
|---|---|---|---|---|
| US_Installation_Game_Assets | 14 structures × (4-view sheet + 4 crops) | 70 | 3 | Sheets for **Barracks, HESCO, Power Generator** are truncated. All their crops are intact. |
| US_Armed_Forces_Personnel_Assets | 12 roles × (6-pose sheet + 6 crops) | 84 | 0 | AT4 pose labels wrong in `manifest.csv` (see §3) |
| US_Ground_Forces_Game_Assets__1_ | 13 vehicles × (sheet + 4 crops) | 65 | 4 | Front three-quarter crops of **Abrams, Avenger, Paladin, HMMWV** are truncated; their sheets are intact, so the crops can be recovered. |
| US_Ground_Forces_Game_Assets | 10 vehicles | 50 | 4 | **Redundant:** all 40 crops are byte-identical to the `__1_` pack, with the same 4 truncated files. Use `__1_` only. |
| US_Aircraft_Game_Assets_Expanded_1 | 11 aircraft | 55 | 3 | **Byte-identical to the earlier upload** (same SHA-256). A-10 / B-2 / F-22 front three-quarter truncated. |
| US_Aircraft_Game_Assets_1 | 9 aircraft | 45 | 0 | Byte-identical to the earlier upload |

**Missing compared with the handoff:** the handoff lists **MOAB, THAAD and Patriot** concepts in the aircraft pack, but no uploaded ZIP contains them. The handoff also mentions a separate handoff file; only the prompts `.md` was provided.

## 2. Problems found in every pack

1. **Crops clipped at the frame:** 23 of 56 installation crops, 68 of 72 personnel crops, 33 of 52 vehicle crops and 39 of 44 aircraft crops have the subject touching the image edge. The 768×512 / 512×512 cells are smaller than the subjects. The importer re-cuts from the contact sheets as one connected silhouette, as it already does for aircraft.
2. **Stray fragments:** many crops contain pieces of the neighbouring view or pose (32 personnel, 15 vehicle, 7 installation). These are removed by the same silhouette cut.
3. **Orientation is not consistent:** vehicle overheads point left (Abrams, Bradley, M113, M88, M777), right (Paladin, MRAP) or down (HMMWV, medical HMMWV, Avenger). Personnel face left or right from pose to pose. Each needs a recorded nose/facing direction, which is done for aircraft and pending for these packs.
4. **Protected emblem:** the **Field Hospital**, **medical HMMWV** and **Army Medic** (armband and bags) use the **red cross**. It's a protected emblem under the Geneva Conventions, and the ICRC asks game makers not to use it. Replace it (for example, with a green medical cross or a fictional faction medical symbol) before any release.
5. **Real designs, names and insignia:** every vehicle and aircraft depicts a real system (Abrams, Bradley, Stryker, HMMWV, etc.) under manufacturer trademarks, with U.S. insignia. This is acceptable for **development builds only**; it needs a rights review before release, as already recorded for the aircraft.

## 3. Pack-specific findings

### Installations (14)
- High-quality, consistent renders; the four views agree.
- **The "overhead" view is not top-down.** It's a steep high-angle three-quarter view that shows the building's front faces. Laid flat on the ground it would look wrong. Used as a **camera-facing building image** (the classic 2.5D RTS approach), it matches our RTS camera angle well.
- **Construction Yard** shows scaffolding and a crane. It can serve as the generic "under construction" visual until staged art (foundation → scaffolding → complete) exists.
- **No team-colour zones and no damaged/destroyed states.** These are needed for gameplay (see `docs/ASSET_GENERATION_README.md` §2.4 / §4.5).

### Personnel (12 roles × 6 poses)
- High quality; the AT4 is correctly **shoulder-braced** in its aiming poses.
- **AT4 `manifest.csv` labels are wrong for 5 of 6 crops.** Actual content by label:

  | Label | Actual pose |
  |---|---|
  | standing_ready | standing, shoulder aim (correct) |
  | walking | crouched aim |
  | running | kneeling aim |
  | crouched_movement | standing carry |
  | kneeling | walking carry |
  | low_profile | running carry |

  Corrected in our import mapping.
- **These are key poses, not animation.** There's one view direction per pose (the README says so too). Usable as camera-facing infantry images that swap pose by state (idle / move / attack / prone) and flip left/right. True 8-direction walking needs more frames or 3D models.

### Ground vehicles (13)
- High quality. Most overheads are truly top-down.
- **Turrets are baked into the overhead.** An Abrams sprite can't traverse its turret, so the whole sprite would have to face the target.
- **Flat top-down vehicles read as "decals"** from the 52° RTS camera, because they show no height. Aircraft don't have this problem because they're seen from above in flight. Recommendation: build tracked and turreted vehicles as **3D models** (like the Vanguard) using these sheets as references. Wheeled vehicles could be trialled as sprites first.
- The **TOW, .50-cal and medical HMMWV** variants are visually distinct and match the handoff's requirement for three different units.

## 4. Integration plan (next milestone: base building and economy)

| Pack | Engine representation | Use |
|---|---|---|
| Installations | Camera-facing image (impostor) at real footprint, with ground shadow decal and selection footprint; construction-yard art as the build stage | Command Center, Barracks, War Factory, Airfield, Supply Depot, Airdrop Zone, Power Plant, Radar, Repair Bay, Field Hospital (emblem replaced), Gatehouse, HESCO, Defense Tower |
| Personnel | Camera-facing pose images with left/right flip | Rifleman, SAW, M240B, AT4 (shoulder-fired), Ranger, Special Forces, Sniper, Medic, EOD Engineer (builder role), pilots and flightline crew as ambient/rescue units |
| Ground vehicles | 3D models from the reference sheets for turreted vehicles; sprite trial for wheeled ones; portraits from the three-quarter views | Abrams, Bradley, Stryker, Paladin, M777, Avenger (anti-air, the counter to helicopters and jets), HMMWV ×4, MRAP, M113, M88 (repair/recovery) |

## 5. What to regenerate or supply

- A-10 front three-quarter view (still truncated in both uploads)
- MOAB, THAAD and Patriot concepts (named in the handoff, not in any ZIP)
- Medical assets without the red cross (Field Hospital, medical HMMWV, Medic)
- Optional: re-export the four ground front three-quarter crops and the three installation sheets (all recoverable here, but the source pack should be fixed)
