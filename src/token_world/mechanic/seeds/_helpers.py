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
