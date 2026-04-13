"""MECH24 contagion seed mechanic — voluntary probabilistic transmission.

Scope
-----
One-step transmission: when invoked on an infected carrier, enumerate
every uninfected agent in the carrier's containing room and, for each,
roll a probability vs. the carrier's ``transmission_rate`` (defaulting
to 0.3). On success, write ``infected=True`` plus an optional
``disease`` tag inherited from the carrier. Already-infected neighbours
are never re-mutated -- that is the reactive-cycle guard required by
cross-AI review Suggestion #10 and mirrors the ``fire_spread`` / 04-08
``pickup`` idioms.

Determinism (GAP-GRAPH05)
-------------------------
``ctx.seed`` / ``ctx._seed`` is a documented framework gap: the
MechanicContext has no seeded-RNG primitive today (see
``docs/guides/authoring-mechanics.md`` § Known gaps). v1 therefore
constructs a local :class:`random.Random` instance per apply, seeded
from the current tick id if accessible via the temporal facade or a
class-level fallback constant otherwise. This is explicitly a
determinism gap: two identical calls within one tick may differ
across processes; under replay the tick id bounds the drift.
GAP-GRAPH05's Phase-5 seeded-RNG primitive replaces the local
Random with ``ctx.seed`` without changing the mechanic's public
shape.

UC-V07 mapping
--------------
Alice (infected, transmission_rate=1.0 in the test fixture, or 0.3
default in the UC manifest) coughs in a co-located office. Contagion's
apply iterates through Bob / Carol / Dave, flipping ``infected=True``
and copying ``disease="common_cold"`` on each successful roll.
transmission_rate=1.0 is the deterministic edge used by unit tests;
transmission_rate=0.0 is the guaranteed-refuse edge.

Phase-5 integration notes
-------------------------
- GAP-ENG07 (passive tick sweep): a future tick-end sweep will invoke
  contagion reactively for every infected carrier without needing an
  explicit manifest action. The mechanic shape is unchanged.
- GAP-GRAPH05 (seeded RNG): swap the local :class:`random.Random`
  construction for ``ctx.seed`` when the primitive lands.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


_DEFAULT_TRANSMISSION_RATE = 0.3
# GAP-GRAPH05 fallback seed: used when no tick id is accessible. Picked
# so a fresh test graph with default transmission_rate (0.3) has a
# reproducible outcome across Python versions.
_FALLBACK_SEED = 42


def _find_containing_room(ctx: MechanicContext, node_id: str) -> str | None:
    """Return the first ``located_in`` out-neighbour of *node_id*, or None."""
    for neighbor in ctx.neighbors(node_id, relation="located_in"):
        return neighbor
    return None


def _resolve_seed(ctx: MechanicContext) -> int:
    """Best-effort tick-aware seed until GAP-GRAPH05 ships ctx.seed.

    Reads an accessible tick id from the temporal facade; falls back to
    :data:`_FALLBACK_SEED` when no tick is in scope. The docstring gap
    citation is the authoritative determinism contract for v1.
    """
    try:
        temporal = ctx.temporal
    except Exception:  # pragma: no cover — defensive
        return _FALLBACK_SEED
    # TemporalIndex exposes the current session tick through
    # get_session_events; fall back silently when the API shape
    # differs. This is a best-effort hook -- Phase 5's ctx.seed
    # replaces it.
    try:
        events = temporal._graph.get_session_events()
    except Exception:  # pragma: no cover -- defensive
        return _FALLBACK_SEED
    if not events:
        return _FALLBACK_SEED
    try:
        # tick_id is a monotonic int on GraphEvent records.
        return int(events[-1].tick_id)
    except Exception:  # pragma: no cover -- defensive
        return _FALLBACK_SEED


class ContagionMechanic(Mechanic):
    """Probabilistic infection spread from a co-located carrier.

    Preconditions (check):
        - Target exists and is infected (``infected=True``).
        - Target has a containing room (``located_in`` out-neighbour).
        - At least one uninfected agent is co-located in that room.

    Side effects (apply):
        - For each uninfected co-located agent, roll
          ``Random(seed).random() < transmission_rate`` and, on
          success, emit ``ctx.mutate(agent, "infected", True)``
          plus -- when the carrier has a ``disease`` tag --
          ``ctx.mutate(agent, "disease", carrier_disease)``.
        - Already-infected neighbours are never mutated.
    """

    id = "contagion"
    description = "Probabilistic infection spread to co-located uninfected agents"
    voluntary = True
    tags: list[str] = ["environmental", "contagion", "disease"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["target does not exist"])

        target_props = ctx.query_node(ctx.target)
        if not target_props.get("infected"):
            return CheckResult(passed=False, reasons=["target is not infected"])

        room = _find_containing_room(ctx, ctx.target)
        if room is None:
            return CheckResult(
                passed=False,
                reasons=["target is not located_in any room"],
            )

        # At least one uninfected co-located agent.
        for neighbor in ctx.find_nodes(infected=False):
            if neighbor == ctx.target:
                continue
            if _find_containing_room(ctx, neighbor) == room:
                return CheckResult(passed=True)
        return CheckResult(
            passed=False,
            reasons=["no uninfected co-located agents"],
        )

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        target_props = ctx.query_node(ctx.target)
        rate_raw = target_props.get("transmission_rate", _DEFAULT_TRANSMISSION_RATE)
        # Accept int or float; coerce to float. bool is rejected (bool-is-int).
        if isinstance(rate_raw, bool) or not isinstance(rate_raw, (int, float)):
            rate = _DEFAULT_TRANSMISSION_RATE
        else:
            rate = float(rate_raw)

        carrier_disease = target_props.get("disease")

        room = _find_containing_room(ctx, ctx.target)
        if room is None:
            return []

        # GAP-GRAPH05 workaround: local Random seeded from the tick id.
        rng = random.Random(_resolve_seed(ctx))

        mutations: list[Mutation] = []
        for neighbor in ctx.find_nodes(infected=False):
            if neighbor == ctx.target:
                continue
            if _find_containing_room(ctx, neighbor) != room:
                continue
            # Reactive-cycle guard: skip already-infected (defensive; the
            # find_nodes(infected=False) filter already excludes them).
            neighbor_props = ctx.query_node(neighbor)
            if neighbor_props.get("infected"):
                continue
            if rng.random() < rate:
                mutations.append(ctx.mutate(neighbor, "infected", True))
                if carrier_disease is not None:
                    mutations.append(ctx.mutate(neighbor, "disease", carrier_disease))
        return mutations
