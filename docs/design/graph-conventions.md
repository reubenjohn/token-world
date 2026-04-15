# Graph Conventions — Canonical Entity Representations

*Phase 18 | Cross-ref: REQ-V12-GRAPH-01..04 and REQ-V12-ENGINE-03*

This document defines canonical property shapes for common world-object categories.
Mechanics must target these shapes to stay interoperable. The engine **never**
privileges any property name — all semantics live in mechanics.

---

## 1. Doors (REQ-V12-GRAPH-01)

A door is an `entity` node. Its state is expressed as emergent properties that any
mechanic may read or set. The engine does not hard-code the word `locked`.

### Canonical properties

| Property | Type | Meaning |
|---|---|---|
| `subtype` | `str` | `"door"` or `"passage"` |
| `state` | `str` | `"open"` \| `"closed"` \| `"locked"` \| `"stuck"` — emergent default `"closed"` |
| `locked` | `bool` | `True` when mechanically locked (shortcut; mechanics may use `state="locked"` instead) |
| `connects` | `list[str]` | Two node IDs the door connects, e.g. `["village_square", "smithy"]` |

### Example

```python
kg.add_node("cottage_door", "entity")
kg.set("cottage_door", "subtype", "door")
kg.set("cottage_door", "state", "closed")
kg.set("cottage_door", "locked", False)
kg.set("cottage_door", "connects", ["cottage_interior", "meadow"])
```

### Willowbrook conformance
`cottage_door` carries `locked` and `connects: [...]` properties — already conforms.

---

## 2. Containers (REQ-V12-GRAPH-02)

A container is an `entity` node that holds other entities via `contains` edges
(see §3 for edge conventions) plus capacity metadata on the container node.

### Canonical properties

| Property | Type | Meaning |
|---|---|---|
| `subtype` | `str` | `"container"` |
| `capacity` | `int` \| `None` | Max items; `None` = unlimited |
| `open` | `bool` | Whether the container is currently openable/accessible |
| `locked` | `bool` | Whether the container is locked (requires a key or mechanic) |

### Contains edge convention

Items *inside* a container are linked with a directed `contains` edge:

```
container_node  --[relation="contains"]-->  item_node
```

The mechanic that places an item in a container calls:

```python
kg.add_edge(container_id, item_id, {"relation": "contains"})
```

To list contents:

```python
contents = [
    target for (source, target, props) in kg.edges(container_id)
    if props.get("relation") == "contains"
]
```

### Example

```python
kg.add_node("old_chest", "entity")
kg.set("old_chest", "subtype", "container")
kg.set("old_chest", "capacity", 10)
kg.set("old_chest", "open", False)
kg.set("old_chest", "locked", True)
```

---

## 3. Portals / Passages (REQ-V12-GRAPH-03)

Passages are directional or bidirectional traversal links between location nodes.
Willowbrook uses `subtype="passage"` on `cottage_door`; three mechanics
(`walk`, `passage_move`, `movement`) converge on this shape.

### Canonical properties (passage node)

| Property | Type | Meaning |
|---|---|---|
| `subtype` | `str` | `"passage"` |
| `connects` | `list[str]` | Two location node IDs |
| `bidirectional` | `bool` | Default `True`; set `False` for one-way portals |
| `passable` | `bool` | Whether the passage is currently traversable |

### Movement edge convention

When an agent traverses a passage, the engine sets `location` on the agent node:

```python
kg.set(agent_id, "location", destination_node_id)
```

No edge is required to record current location — the `location` property is
sufficient and cheaper to query.

### Example

```python
kg.add_node("north_gate", "entity")
kg.set("north_gate", "subtype", "passage")
kg.set("north_gate", "connects", ["village_square", "forest_path"])
kg.set("north_gate", "bidirectional", True)
kg.set("north_gate", "passable", True)
```

---

## 4. Fungible Amounts (REQ-V12-GRAPH-04)

Fungible resources (water, coins, grain) are represented as `entity` nodes carrying
an `amount` property plus a `unit` label. Mechanics manipulate `amount` directly;
the engine never inspects it.

### Canonical properties

| Property | Type | Meaning |
|---|---|---|
| `subtype` | `str` | `"resource"` or a domain label like `"currency"`, `"fluid"` |
| `amount` | `int` \| `float` | Quantity of the resource |
| `unit` | `str` | Human-readable unit: `"litres"`, `"coins"`, `"kg"` |
| `owner` | `str` \| `None` | Node ID of the holding agent (or container) |

### Example — Mira's water bucket

```python
kg.add_node("drawn_water", "entity")
kg.set("drawn_water", "subtype", "fluid")
kg.set("drawn_water", "amount", 10)
kg.set("drawn_water", "unit", "litres")
kg.set("drawn_water", "owner", "mira")
```

Split / merge patterns:

```python
# Pour 3 litres into a cup
current = kg.query("drawn_water").get("amount", 0)
kg.set("drawn_water", "amount", current - 3)
kg.add_node("cup_of_water", "entity")
kg.set("cup_of_water", "subtype", "fluid")
kg.set("cup_of_water", "amount", 3)
kg.set("cup_of_water", "unit", "litres")
```

---

## Engine invariant

The engine **never** reads `locked`, `blocked`, `inventory_full`, or any other
semantic property to gate actions. These names are meaningful only to mechanics.
See REQ-V12-ENGINE-03 for the audit that enforces this.

All conventions in this document are *recommendations* for seed and operator
mechanics. The graph accepts any property; these shapes maximise interoperability
between independently authored mechanics.
