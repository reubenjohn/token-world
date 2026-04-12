"""Optional R-tree spatial index over KnowledgeGraph nodes with 2D position data.

This module is a **derived view** over the KnowledgeGraph — it is never a source
of truth. The index can be fully **rebuildable** from graph state alone; any
drift between the index and the graph is resolved by calling :meth:`rebuild`.

Nodes are indexed when they carry either:

- ``position = [x, y]`` — a 2D point (inserted as a zero-area bbox ``(x, y, x, y)``).
- ``bbox = [minx, miny, maxx, maxy]`` — an axis-aligned 2D bounding box.

If both are present, ``bbox`` wins. Nodes with neither property are silently
skipped (no error, not indexed). Malformed values (wrong length, non-numeric)
are logged as a warning via loguru and also skipped — robustness for
gap-analysis scenarios where authors may hand-craft test graphs.

Only nodes are indexed; edges are not. See phase 03 research notes for
rationale.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger
from rtree import index as _rtree_index

if TYPE_CHECKING:
    from token_world.graph.knowledge_graph import KnowledgeGraph


# Public bbox tuple types for type hints.
_Point = tuple[float, float]
_Bbox = tuple[float, float, float, float]


def _coerce_bbox(props: dict) -> _Bbox | None:
    """Return a 4-tuple bbox from node props or ``None`` if not indexable.

    ``bbox`` wins over ``position`` when both are present. Raises
    ``ValueError`` on malformed shapes (caller converts to a warning + skip).
    """
    bbox = props.get("bbox")
    if bbox is not None:
        if not isinstance(bbox, list) or len(bbox) != 4:
            raise ValueError(f"bbox must be a list of 4 numbers, got {bbox!r}")
        if not all(isinstance(v, int | float) and not isinstance(v, bool) for v in bbox):
            raise ValueError(f"bbox values must be numeric, got {bbox!r}")
        return (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
    position = props.get("position")
    if position is not None:
        if not isinstance(position, list) or len(position) != 2:
            raise ValueError(f"position must be a list of 2 numbers, got {position!r}")
        if not all(isinstance(v, int | float) and not isinstance(v, bool) for v in position):
            raise ValueError(f"position values must be numeric, got {position!r}")
        x, y = float(position[0]), float(position[1])
        return (x, y, x, y)
    return None


class SpatialIndex:
    """R-tree spatial index over a :class:`KnowledgeGraph`.

    The index is a **derived, rebuildable** projection of graph state — it is
    never a source of truth. Callers construct an instance, then invoke
    :meth:`rebuild` to populate it, and finally use :meth:`nearest`,
    :meth:`within`, or :meth:`intersects` to query.

    Typical use is via the lazy ``MechanicContext.spatial`` accessor, which
    constructs and rebuilds this index on first access within a mechanic's
    check/apply cycle.
    """

    def __init__(self, graph: KnowledgeGraph) -> None:
        self._graph = graph
        self._rtree: _rtree_index.Index = _rtree_index.Index(
            properties=_rtree_index.Property(dimension=2)
        )
        # Bidirectional mapping: rtree requires int ids, we expose node_ids.
        self._id_to_node: dict[int, str] = {}
        self._node_to_id: dict[str, int] = {}
        # Cache a copy of the bbox per node so intersects() can look it up
        # without replaying validation.
        self._node_to_bbox: dict[str, _Bbox] = {}
        self._next_int_id: int = 0

    # --- Build / rebuild ---

    def rebuild(self) -> None:
        """Drop all entries and re-scan the graph.

        Derived view contract: after ``rebuild()`` the index mirrors the
        current graph state. Safe to call repeatedly; idempotent when the
        graph is unchanged.
        """
        # Fresh rtree — faster than per-id deletions for full rebuild.
        self._rtree = _rtree_index.Index(properties=_rtree_index.Property(dimension=2))
        self._id_to_node.clear()
        self._node_to_id.clear()
        self._node_to_bbox.clear()
        self._next_int_id = 0

        for node_id in self._graph.nodes():
            try:
                props = self._graph.query(node_id)
            except KeyError:  # pragma: no cover — node removed mid-iteration
                continue
            try:
                bbox = _coerce_bbox(props)
            except ValueError as exc:
                logger.warning(
                    "SpatialIndex: skipping node {!r} — invalid position/bbox: {}",
                    node_id,
                    exc,
                )
                continue
            if bbox is None:
                continue
            int_id = self._next_int_id
            self._next_int_id += 1
            self._rtree.insert(int_id, bbox)
            self._id_to_node[int_id] = node_id
            self._node_to_id[node_id] = int_id
            self._node_to_bbox[node_id] = bbox

    # --- Filter helper ---

    def _passes_filter(
        self,
        node_id: str,
        *,
        node_type: str | None,
        subtype: str | None,
    ) -> bool:
        if node_type is None and subtype is None:
            return True
        try:
            props = self._graph.query(node_id)
        except KeyError:  # pragma: no cover
            return False
        if node_type is not None and props.get("type") != node_type:
            return False
        return not (subtype is not None and props.get("subtype") != subtype)

    # --- Queries ---

    def nearest(
        self,
        point: _Point,
        *,
        k: int = 1,
        node_type: str | None = None,
        subtype: str | None = None,
    ) -> list[str]:
        """Return up to ``k`` nearest node_ids to ``point`` (Euclidean).

        Filtering by ``node_type`` / ``subtype`` is applied after the rtree
        query, so the returned list may contain fewer than ``k`` entries. If
        the index contains fewer than ``k`` nodes in total, returns them all.
        """
        x, y = float(point[0]), float(point[1])
        # Over-fetch when filters are active so we can still satisfy k after
        # post-filtering. When no filter, rtree already caps at k.
        fetch = k if (node_type is None and subtype is None) else max(k * 4, k)
        fetch = min(fetch, len(self._id_to_node)) or k
        if not self._id_to_node:
            return []
        raw_ids = list(self._rtree.nearest((x, y, x, y), fetch))
        results: list[str] = []
        for int_id in raw_ids:
            node_id = self._id_to_node.get(int_id)
            if node_id is None:
                continue
            if not self._passes_filter(node_id, node_type=node_type, subtype=subtype):
                continue
            results.append(node_id)
            if len(results) >= k:
                break
        return results

    def within(
        self,
        bbox: _Bbox,
        *,
        node_type: str | None = None,
        subtype: str | None = None,
    ) -> list[str]:
        """Return node_ids whose point/bbox intersects ``bbox``."""
        minx, miny, maxx, maxy = (
            float(bbox[0]),
            float(bbox[1]),
            float(bbox[2]),
            float(bbox[3]),
        )
        results: list[str] = []
        for int_id in self._rtree.intersection((minx, miny, maxx, maxy)):
            node_id = self._id_to_node.get(int_id)
            if node_id is None:
                continue
            if not self._passes_filter(node_id, node_type=node_type, subtype=subtype):
                continue
            results.append(node_id)
        return results

    def intersects(
        self,
        node_id: str,
        *,
        node_type: str | None = None,
        subtype: str | None = None,
    ) -> list[str]:
        """Return node_ids whose bbox overlaps ``node_id``'s bbox (excluding self).

        Raises:
            ValueError: If ``node_id`` has no position or bbox (nothing to
                compare against).
        """
        bbox = self._node_to_bbox.get(node_id)
        if bbox is None:
            raise ValueError(
                f"Node {node_id!r} is not indexed (no position or bbox). "
                "Cannot compute intersects()."
            )
        hits = self.within(bbox, node_type=node_type, subtype=subtype)
        return [n for n in hits if n != node_id]
