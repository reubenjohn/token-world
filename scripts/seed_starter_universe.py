"""Seed a starter universe designed to invite emergent mechanic authoring.

Run::

    uv run python scripts/seed_starter_universe.py [--slug willowbrook] [--overwrite]

What it builds:

- **Willowbrook** — a tiny cottage + garden scene. Two rooms, seven entities
  with emergent hooks (a locked chest, a well with a water level, a garden
  bed with fertility, a whetstone, a cat, a knife, a hearth). One resident
  agent, *Mira*, a curious apprentice eager to explore and fix things.

- All bundled seed mechanics are auto-copied by the scaffolder (``speak``,
  ``look``, ``movement``, ``pickup``, ``give``, ``sleep``, ``trade``,
  ``teach``, ``craft``, etc.). Emergent actions — *"water the garden"*,
  *"sharpen my knife on the whetstone"*, *"peer into the well"*,
  *"pick the lock on the old chest"* — have no matching mechanic by design,
  so the engine will yield to the operator on first use.

- Writes the seed graph, creates Mira's personality bundle + first session,
  and leaves the universe ready for ``token-world playtest`` /
  ``scripts/run_unattended.py``.

The personality is hand-crafted (not generated via Sonnet) so seeding is
deterministic and free.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger

from token_world.graph import KnowledgeGraph
from token_world.resident import (
    PersonalityBundle,
    SessionManager,
    create_agent_node,
)
from token_world.universe.manager import UniverseManager

DEFAULT_SLUG = "willowbrook"

MIRA = PersonalityBundle(
    name="Mira",
    archetype="curious apprentice",
    traits=["inquisitive", "earnest", "stubborn", "tinkerer", "kind"],
    backstory=(
        "Apprenticed to Old Bran the hedge-witch two winters ago, Mira learned "
        "to read the weather from swallow flights and to mend a broken latch "
        "with river clay. She is eleven, or maybe twelve — nobody's entirely "
        "sure, including her. She is very sure she'd like to know what's "
        "inside the old chest in the cottage, and whether the well has a "
        "bottom."
    ),
    speech_style=(
        "Plain, observant, mildly stubborn. Asks questions other people "
        "forget to ask. Occasionally hums. Never sulks for long."
    ),
)


# Minimal seed for Willowbrook — just enough that Mira can observe her
# surroundings and move around. The 5 new framework-level seed mechanics
# (examine, pet, sharpen, hum, drop) are also included so common verbs resolve
# immediately on the first tick without requiring an operator yield.
# Everything else (watering, planting, peering, forcing locks, drawing water)
# must be authored by the operator the first time Mira tries it, which is
# exactly the emergence we want.
_KEEP_MECHANICS = frozenset(
    {
        "look.py",
        "observation.py",
        "movement.py",
        "passage_move.py",
        "position_sync.py",
        "speak.py",
        "pickup.py",
        "environmental_reaction.py",
        "_helpers.py",  # shared helpers used by the above
        # New framework-level seed mechanics (REQ-V12-SEEDS-01)
        "examine.py",
        "pet.py",
        "sharpen.py",
        "hum.py",
        "drop.py",
    }
)


def _prune_seed_mechanics(universe_dir: Path) -> None:
    """Remove all seed mechanics except the minimal set in :data:`_KEEP_MECHANICS`.

    The full scaffolder copies ~30 seed mechanics including LRA-triggering
    ones (``daydream``, ``sleep``, ``autopilot_*``, ``drunk``) that starve a
    starter universe of turns. We keep only the primitives a resident needs
    to orient herself; operator-authored mechanics fill everything else.

    Prints a loud warning to stderr listing every file that will be removed,
    so operators who re-seed an existing universe notice before data is lost.
    Use ``--preserve-mechanics`` to skip this call entirely.
    """
    mech_dir = universe_dir / "mechanics"
    to_remove = sorted(py for py in mech_dir.glob("*.py") if py.name not in _KEEP_MECHANICS)
    if to_remove:
        print(
            "WARNING: seed_starter_universe.py will overwrite the following "
            "mechanics (use --preserve-mechanics to keep them):",
            file=sys.stderr,
        )
        for py in to_remove:
            print(f"  {py.name}", file=sys.stderr)
    for py in to_remove:
        py.unlink()
    logger.info("Pruned {} seed mechanics; kept {}", len(to_remove), sorted(_KEEP_MECHANICS))


def _seed_graph(kg: KnowledgeGraph) -> dict[str, str]:
    """Populate the knowledge graph with the starter scene. Returns ID map."""
    ids: dict[str, str] = {}

    # --- Rooms ------------------------------------------------------------
    cottage = kg.claim_id("cottage_interior")
    garden = kg.claim_id("garden")
    kg.add_node(cottage, node_type="entity")
    kg.set(cottage, "subtype", "room")
    kg.set(cottage, "description", "A snug, soot-smudged cottage room with a hearth and a chest.")
    kg.set(cottage, "illumination", 0.7)
    kg.set(cottage, "temperature", 0.65)

    kg.add_node(garden, node_type="entity")
    kg.set(garden, "subtype", "room")
    kg.set(
        garden,
        "description",
        "A small tended garden behind the cottage, with a well and a bed of dark loam.",
    )
    kg.set(garden, "illumination", 0.95)
    kg.set(garden, "temperature", 0.45)
    kg.set(garden, "weather", "overcast")

    # Room adjacency — a door
    door = kg.claim_id("cottage_door")
    kg.add_node(door, node_type="entity")
    kg.set(door, "subtype", "passage")
    kg.set(door, "connects", [cottage, garden])
    kg.set(door, "locked", False)
    kg.add_edge(cottage, door, relation="contains")
    kg.add_edge(garden, door, relation="contains")

    # --- Entities in the cottage -----------------------------------------
    hearth = kg.claim_id("hearth")
    kg.add_node(hearth, node_type="entity")
    kg.set(hearth, "subtype", "fire")
    kg.set(hearth, "lit", True)
    kg.set(hearth, "warmth", 0.9)
    kg.set(hearth, "fuel_level", 0.6)
    kg.set(
        hearth,
        "description",
        "A low fire in a blackened stone hearth; a kettle hooked above it.",
    )
    kg.add_edge(cottage, hearth, relation="contains")

    chest = kg.claim_id("old_chest")
    kg.add_node(chest, node_type="entity")
    kg.set(chest, "subtype", "container")
    kg.set(chest, "locked", True)
    kg.set(chest, "material", "oak")
    kg.set(chest, "contents", [])  # hidden from sight; operator can reveal when opened
    kg.set(chest, "description", "An old iron-bound chest, squat and heavy. The lock is tarnished.")
    kg.add_edge(cottage, chest, relation="contains")

    cat = kg.claim_id("tabby_cat")
    kg.add_node(cat, node_type="entity")
    kg.set(cat, "subtype", "animal")
    kg.set(cat, "species", "cat")
    kg.set(cat, "name", "Pip")
    kg.set(cat, "mood", "purring")
    kg.set(cat, "hunger", 0.3)
    kg.set(cat, "description", "A tabby cat named Pip, curled on a rug near the hearth.")
    kg.add_edge(cottage, cat, relation="contains")

    # --- Entities in the garden ------------------------------------------
    well = kg.claim_id("stone_well")
    kg.add_node(well, node_type="entity")
    kg.set(well, "subtype", "water_source")
    kg.set(well, "water_level", 0.7)
    kg.set(well, "depth_m", 6.0)
    kg.set(
        well,
        "description",
        "A round stone well, mossed at the rim. Cold air rises from inside.",
    )
    kg.add_edge(garden, well, relation="contains")

    bed = kg.claim_id("garden_bed")
    kg.add_node(bed, node_type="entity")
    kg.set(bed, "subtype", "planting_ground")
    kg.set(bed, "fertility", 0.55)
    kg.set(bed, "planted", [])  # list of plant IDs when something's planted
    kg.set(bed, "moisture", 0.4)
    kg.set(bed, "description", "A bed of dark loam, recently turned. Empty but waiting.")
    kg.add_edge(garden, bed, relation="contains")

    whetstone = kg.claim_id("whetstone")
    kg.add_node(whetstone, node_type="entity")
    kg.set(whetstone, "subtype", "tool")
    kg.set(whetstone, "material", "stone")
    kg.set(
        whetstone,
        "description",
        "A flat grey whetstone on a low bench, worn smooth in the middle.",
    )
    kg.add_edge(garden, whetstone, relation="contains")

    bench = kg.claim_id("bench")
    kg.add_node(bench, node_type="entity")
    kg.set(bench, "subtype", "furniture")
    kg.set(bench, "material", "wood")
    kg.set(bench, "weathered", True)
    kg.set(bench, "planks_intact", 5)
    kg.set(bench, "description", "A low wooden bench beside the whetstone, darkened by weather.")
    kg.add_edge(garden, bench, relation="contains")

    chicken_coop = kg.claim_id("chicken_coop")
    kg.add_node(chicken_coop, node_type="entity")
    kg.set(chicken_coop, "subtype", "structure")
    kg.set(chicken_coop, "chickens_inside", 3)
    kg.set(chicken_coop, "door_latched", True)
    kg.set(chicken_coop, "eggs_today", 0)
    kg.set(chicken_coop, "feed_level", 0.6)
    kg.set(chicken_coop, "description", "A small coop of wattle and thatch; clucking from within.")
    kg.add_edge(garden, chicken_coop, relation="contains")

    broken_gate = kg.claim_id("broken_gate")
    kg.add_node(broken_gate, node_type="entity")
    kg.set(broken_gate, "subtype", "gate")
    kg.set(broken_gate, "broken", True)
    kg.set(broken_gate, "latched", False)
    kg.set(broken_gate, "repair_progress", 0.0)
    kg.set(broken_gate, "material", "wood")
    kg.set(broken_gate, "description", "The garden gate hangs at an angle, one hinge torn loose.")
    kg.add_edge(garden, broken_gate, relation="contains")

    # --- Mira's inventory -------------------------------------------------
    knife = kg.claim_id("pocket_knife")
    kg.add_node(knife, node_type="entity")
    kg.set(knife, "subtype", "tool")
    kg.set(knife, "material", "steel")
    kg.set(knife, "sharpness", 0.35)
    kg.set(knife, "description", "A small pocket knife, nicked but serviceable. A bit dull.")

    # --- Resident agent --------------------------------------------------
    mira_id = kg.claim_id("mira")
    create_agent_node(kg, mira_id, MIRA)
    kg.set(mira_id, "located_in", cottage)
    kg.set(mira_id, "position", [2.0, 1.5])
    kg.set(mira_id, "health", 1.0)
    kg.set(mira_id, "energy", 0.8)
    kg.set(mira_id, "inventory", [knife])
    kg.set(mira_id, "mood", "curious")
    kg.set(mira_id, "last_heard", [])

    kg.add_edge(mira_id, knife, relation="carries")

    ids.update(
        cottage=cottage,
        garden=garden,
        door=door,
        hearth=hearth,
        chest=chest,
        cat=cat,
        well=well,
        bed=bed,
        whetstone=whetstone,
        bench=bench,
        chicken_coop=chicken_coop,
        broken_gate=broken_gate,
        knife=knife,
        mira=mira_id,
    )
    return ids


def seed(
    slug: str = DEFAULT_SLUG,
    *,
    overwrite: bool = False,
    preserve_mechanics: bool = False,
) -> Path:
    """Create (or re-create) the starter universe; return its path."""
    manager = UniverseManager()
    if overwrite:
        try:
            manager.delete(slug)
            logger.info("Deleted existing universe '{}'", slug)
        except FileNotFoundError:
            pass

    universe_dir = manager.create("Willowbrook")
    logger.info("Scaffolded universe at {}", universe_dir)

    if not preserve_mechanics:
        _prune_seed_mechanics(universe_dir)
    else:
        print("--preserve-mechanics set; skipping mechanic pruning.", file=sys.stderr)
        logger.info("--preserve-mechanics set; skipping mechanic pruning")

    kg = KnowledgeGraph(db_path=universe_dir / "universe.db")
    ids = _seed_graph(kg)
    kg.save()
    logger.info("Seeded {} nodes into graph", len(ids))

    sessions = SessionManager(universe_dir / "universe.db")
    session_id = sessions.create_session(ids["mira"], MIRA)
    logger.info("Opened session {} for agent {}", session_id, ids["mira"])

    print(f"Universe '{slug}' ready at {universe_dir}")
    print(f"  resident agent: {ids['mira']}  ({MIRA.name})")
    print(f"  session_id: {session_id}")
    print(f"  rooms: {ids['cottage']}, {ids['garden']}")
    print("  entities with emergent hooks:")
    for key in ("chest", "well", "bed", "whetstone", "cat", "hearth"):
        print(f"    - {ids[key]}")
    print()
    print(
        "Next: TOKEN_WORLD_BACKEND=claude-cli uv run python scripts/run_unattended.py "
        f"--slug {slug} --ticks 20"
    )
    return universe_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", default=DEFAULT_SLUG)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--preserve-mechanics",
        action="store_true",
        default=False,
        help=(
            "Skip pruning of mechanics/*.py files. Use when re-seeding a universe "
            "that has operator-authored mechanics you want to preserve."
        ),
    )
    args = parser.parse_args()

    try:
        seed(args.slug, overwrite=args.overwrite, preserve_mechanics=args.preserve_mechanics)
    except FileExistsError as e:
        print(f"Error: {e}  (pass --overwrite to recreate)", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
