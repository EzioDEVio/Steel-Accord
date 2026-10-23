# Transports (M4) - rules as implemented

- **Who is a transport:** only units whose definition has a `transport` block (`scripts/unit_defs.gd`): HMMWV (5),
  M-ATV MRAP (4), M113 (8), Stryker (9), Bradley (6), UH-60 (8); Iran: BMP-2 (7), Boragh (8). Capacity and accepted
  passenger types (infantry only) are data. The supply CH-47 / CH-47C is never a troop transport.
- **Boarding:** select infantry and left-click a friendly transport with room (`commander.gd`). Units walk to it and
  board when close; passengers leave the simulation (`battle.units`) while aboard and keep health and veterancy.
- **Unloading:** D or "Unload all" (all passengers), or a passenger tile (one). Helicopters hover low first.
  Passengers are placed on free ground around the vehicle (`battle.unload_one`), never inside obstacles.
- **Passengers do not fire from inside.**
- **Transport destroyed:** all passengers are lost; the player is told ("<vehicle> destroyed - N passengers lost").
- **Tests:** `autotest_base.gd` `_qa_m1`: board_transport, unload_transport, air_assault_board, air_assault_unload.
