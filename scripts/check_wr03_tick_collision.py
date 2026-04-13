"""WR-03 investigation: does restore() after conservation rollback cause tick ID collision?

Simulates the engine's run_tick → conservation violation → restore() → next run_tick
sequence at the KnowledgeGraph level to verify whether tick IDs collide.

Usage: uv run python scripts/check_wr03_tick_collision.py
"""

from __future__ import annotations

import tempfile

from token_world.graph import KnowledgeGraph


def main() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    kg = KnowledgeGraph(db_path=db_path)

    # Simulate run_tick tick 1: engine does set_tick then snapshot
    next_tick = kg.current_tick + 1  # = 1
    kg.set_tick(next_tick)
    print(f"Tick 1: set_tick({next_tick}) → current_tick={kg.current_tick}")

    snap_id = kg.snapshot(next_tick, summary=f"pre-tick {next_tick}")
    print(
        f"Tick 1: snapshot(tick_id={next_tick}) → snap_id={snap_id}, current_tick={kg.current_tick}"
    )

    # Simulate conservation violation → restore
    kg.restore(snap_id)
    print(f"Tick 1: restore(snap_id={snap_id}) → current_tick={kg.current_tick}")

    # Simulate next run_tick (tick 2)
    next_tick_2 = kg.current_tick + 1
    print(f"Tick 2: would use next_tick={next_tick_2}")

    collision = next_tick == next_tick_2
    print(f"\nCollision between tick 1 ID ({next_tick}) and tick 2 ID ({next_tick_2})? {collision}")

    if collision:
        print("PROBLEM: two run_tick calls would get the same tick_id string.")
    else:
        print("OK: no collision — reviewer's concern is about the snapshot tick value.")
        print("Confirmed: restore() sets current_tick=next_tick so next run_tick gets next_tick+1.")


if __name__ == "__main__":
    main()
