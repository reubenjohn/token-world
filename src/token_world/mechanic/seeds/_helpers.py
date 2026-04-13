"""Shared helpers for seed mechanics.

Registry skips ``_*.py`` files during discovery (D-05), so this module is
registry-invisible and safe to grow organically as seeds identify common
patterns worth extracting. Per D-11, helpers graduate from inline duplication
to this module only after ≥3 shared uses across seeds (D-11 / authoring
guide §7).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from token_world.graph import Mutation
    from token_world.mechanic.context import MechanicContext


# Subtypes that count as passage-like entities. Extend by editing this set —
# kept here (not in a seed module) so multiple seeds can share the
# classification. ``passage_move``'s helper references it; a future
# ``try_door`` mechanic (plan 04-07 MECH27) will reuse the same set.
_PASSAGE_SUBTYPES: frozenset[str] = frozenset({"doorway", "passage", "bridge"})


def _is_passage_open(props: dict) -> bool:
    """Return True if a passage entity's props indicate it is traversable.

    Doorways carry ``open=True``. Bridges carry ``traversable=True``. Either
    one counts as "passable" for movement. When neither is present we fall
    back to ``open=True`` (the canonical doorway default); an explicit
    ``open=False`` always blocks.
    """
    if "open" in props:
        return bool(props.get("open"))
    if "traversable" in props:
        return bool(props.get("traversable"))
    # No gate marker at all → assume the author meant "open".
    return True


def _find_open_passage(ctx: MechanicContext, src: str, dst: str) -> str | None:
    """Return the id of an open passage entity connecting *src* to *dst*.

    Walks *src*'s outgoing ``connects`` edges looking for an entity P whose
    ``subtype`` is one of ``_PASSAGE_SUBTYPES`` and whose props mark it as
    open (``open=True`` for doorways, ``traversable=True`` for bridges). P
    must itself have a ``connects`` edge to *dst*.

    Returns ``None`` when no such passage exists. The helper does NOT treat a
    direct ``src --connects--> dst`` edge as a passage — that's a
    separate path handled by the caller (``passage_move`` accepts direct
    connects as a distinct success branch).

    Shared with plan 04-07's ``try_door`` MECH27 (D-11 "after 3 shared uses"
    threshold reached once that lands — this is use #2 after the initial
    ``passage_move`` implementation).

    Args:
        ctx: Mechanic execution context.
        src: Source node id (e.g. actor's current located_in room).
        dst: Destination node id.

    Returns:
        The passage entity's id, or ``None`` when no open passage mediates
        ``src → dst``.
    """
    for neighbor in ctx.neighbors(src, relation="connects"):
        props = ctx.query_node(neighbor)
        if props.get("subtype") not in _PASSAGE_SUBTYPES:
            continue
        if not _is_passage_open(props):
            continue
        # The passage must itself connect onward to dst.
        if dst in set(ctx.neighbors(neighbor, relation="connects")):
            return neighbor
    return None


def _current_location(ctx: MechanicContext, actor: str) -> str | None:
    """Return the actor's current ``located_in`` target, or ``None``.

    A small convenience shared by the three spatial seeds (passage_move,
    terrain_move, position_sync) so they can't each drift to a different
    "what location is the actor in?" semantics. Returns the first
    ``located_in`` out-neighbor; callers assuming a single location are
    responsible for enforcing that invariant in their own ``check``.
    """
    for n in ctx.neighbors(actor, relation="located_in"):
        return n
    return None


def _find_matching_key(
    ctx: MechanicContext,
    actor: str,
    required_key_id: str,
) -> str | None:
    """Return id of a held entity whose ``key_id`` matches, or ``None``.

    Walks *actor*'s outgoing ``holds`` edges and picks the first entity
    whose ``key_id`` property equals *required_key_id*. Used by
    ``try_door`` to gate the "unlock" branch — the door's
    ``required_key_id`` is compared against every held key until a match
    is found. When no held entity matches (no key or wrong key), returns
    ``None`` and the caller refuses with a narrative.

    Shared with the refusal-narrative pattern so a future ``pick_lock``
    or ``try_chest`` mechanic (04-08+) can reuse the same helper without
    reinventing the holds-walk.
    """
    for held in ctx.neighbors(actor, relation="holds"):
        props = ctx.query_node(held)
        if props.get("key_id") == required_key_id:
            return held
    return None


def _count_holds(ctx: MechanicContext, actor: str) -> int:
    """Return the number of outgoing ``holds`` edges from *actor*.

    Shared inventory-count primitive for object-interaction seeds (04-08
    cluster). ``pickup``'s ``inventory_cap`` check and ``give``'s "actor
    must hold the item" gate both read this same count.

    Keeping the count in one place means a future "container nesting"
    design (Phase 8, UC-R04 defer note) only has to re-implement the
    semantics here -- every seed mechanic inherits the new behaviour.

    Args:
        ctx: Mechanic execution context.
        actor: Node id whose outgoing holds edges to count.

    Returns:
        Integer count of ``holds`` out-neighbors from *actor*. Returns 0
        when *actor* holds nothing (or has no outgoing edges at all).
    """
    return sum(1 for _ in ctx.neighbors(actor, relation="holds"))


def _subset_sum(values: list[int], target: int) -> list[int] | None:
    """Return indices of *values* whose sum equals *target*, or ``None``.

    Backtracking search over the held-coin denominations. Used by
    ``fungible_pay`` (MECH18) to pick an exact subset of coin entities
    summing to ``actor.pending_payment["amount"]``. Phase 4 use cases keep
    coin counts small (≤ ~20); the exponential worst case is acceptable
    until a real optimization need surfaces.

    Contract:
        - Returns the FIRST exact-sum subset found (depth-first, descending
          index order). The caller treats the choice as opaque -- UC-R06's
          vignette states the shopkeeper "doesn't care which combination".
        - Returns ``None`` for empty *values*, non-positive *target*, or
          when no exact subset exists. Paying 0 is not a meaningful
          transfer; the caller should guard separately.
        - Negative values are not expected (denominations are positive
          integers); behaviour is undefined for them.

    GAP-MECH29 (change-making — overpay + emit "change-owed" state) is
    deferred; ``fungible_pay`` refuses with a narrative when this helper
    returns ``None`` rather than overpaying.

    Args:
        values: List of positive integers to choose from.
        target: Exact sum required.

    Returns:
        A list of indices into *values* whose values sum to *target*, or
        ``None`` when no exact subset exists.
    """
    if target <= 0 or not values:
        return None

    # Quick reject: target unreachable.
    if sum(values) < target:
        return None

    chosen: list[int] = []

    def _dfs(start: int, remaining: int) -> bool:
        if remaining == 0:
            return True
        if remaining < 0 or start >= len(values):
            return False
        for i in range(start, len(values)):
            chosen.append(i)
            if _dfs(i + 1, remaining - values[i]):
                return True
            chosen.pop()
        return False

    if _dfs(0, target):
        return list(chosen)
    return None


def _refuse_with_narrative(
    ctx: MechanicContext,
    actor: str,
    narrative: str,
    target: str | None = None,
) -> list[Mutation]:
    """Emit refusal-narrative mutations on *actor*.

    Shared helper for the "voluntary refusal with narrative" pattern
    established by 04-07's ``try_door`` (UC-E06). A mechanic's ``apply``
    returns this helper's output when its ``check`` passed but a
    downstream precondition inside ``apply`` ruled out the canonical
    side effect (e.g. ``pickup`` where the actor already holds the
    target, or ``consume`` where a non-food is held).

    This helper deliberately writes the narrative to the *actor*
    (not the target). Phase 5's harness-level refusal-narrative
    synthesis (owned by 04-04's Extension Contract) will eventually
    consume ``last_refusal_narrative`` + ``last_refusal_target`` for
    observation generation. Until then, seeds write these props
    directly -- they are graph-resident ground truth and survive
    restart like every other property.

    Note on check-fail vs. apply-refuse: when a mechanic's ``check``
    returns ``passed=False``, the engine never calls ``apply``, so this
    helper never fires for that path. The Phase-4 harness does not yet
    synthesize narratives from ``CheckResult.reasons`` -- that is a
    harness concern owned by 04-04. Authors who need a narrative on a
    voluntary refusal should let ``check`` pass on "the action is
    coherent" and move the refusal discriminator into ``apply``, as
    ``pickup`` does with the inventory-full branch.

    Args:
        ctx: Mechanic execution context.
        actor: Node id to write the narrative onto.
        narrative: Human-readable refusal message.
        target: Optional target node id; when provided, also writes
            ``last_refusal_target`` for observation-side grounding.

    Returns:
        A list of 1 or 2 mutations (2 when *target* is provided).
    """
    muts: list[Mutation] = [ctx.mutate(actor, "last_refusal_narrative", narrative)]
    if target is not None:
        muts.append(ctx.mutate(actor, "last_refusal_target", target))
    return muts
