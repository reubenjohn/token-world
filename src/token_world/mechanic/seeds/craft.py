"""MECH14 craft seed: recipe-driven multi-input consumption into a new output.

Canonical conservation case with >1 input: remove N held entities,
create one output node, add a holds edge on the actor for the
output. The recipe declares which inputs are needed and what the
output looks like.

Recipe convention
-----------------
The target (a workstation or tool entity such as ``forge``) carries:

    target.recipe = {
        "inputs": ["<node_id_1>", "<node_id_2>", ...],
        "output_subtype": "sword",
        "output_name": "sword",  # optional; defaults to output_subtype
        "output_props": {"mass": 1.3, ...},  # optional
    }

The ``inputs`` list names the specific entity ids the actor must
hold at this moment. A future "recipe by subtype" generalisation
(e.g. "any iron ingot") can compose on top of this primitive once
Phase 8 ships the container subtype.

UC-R01 mapping
--------------
forge carries ``recipe = {"inputs": ["iron_ingot", "wood_plank"],
"output_subtype": "sword"}``. alice holds both inputs. apply
removes both input nodes (which drops their holds edges as a
consequence), claims a unique id for "sword" via ``ctx.claim_id``,
adds the new entity with ``subtype="sword"``, and attaches it with
a holds edge from alice. UC-R01's expected_observations chain:

    - ``not_has_edge(alice, iron_ingot, "holds")`` ✓
    - ``not_has_edge(alice, wood_plank, "holds")`` ✓
    - ``has_property(alice, "inventory_cap")`` ✓ (untouched)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from token_world.graph import Mutation
from token_world.mechanic.protocol import CheckResult, Mechanic
from token_world.mechanic.seeds._helpers import _refuse_with_narrative

if TYPE_CHECKING:
    from token_world.mechanic.context import MechanicContext


_NARRATIVE_NO_RECIPE: str = "target has no recipe"
_NARRATIVE_MISSING_INPUT: str = "required input not held"


class CraftMechanic(Mechanic):
    """Consume recipe inputs held by the actor; produce a new entity.

    Preconditions (check):
        - Actor and target exist.
        - Target carries a ``recipe`` dict with ``inputs`` (list of
          node ids) and ``output_subtype`` (str).

    Side effects (apply):
        - Each input node is removed (``remove_node``).
        - A new entity is created via ``ctx.claim_id`` +
          ``ctx.add_node`` with the recipe's output subtype (plus
          any ``output_props``).
        - A ``holds`` edge is added from actor to the new entity.
    """

    id = "craft"
    description = "Consume held recipe inputs and produce a new entity"
    voluntary = True
    tags: list[str] = ["resource", "crafting"]

    def check(self, ctx: MechanicContext) -> CheckResult:
        if not ctx.has_node(ctx.actor):
            return CheckResult(passed=False, reasons=["actor does not exist"])
        if not ctx.has_node(ctx.target):
            return CheckResult(passed=False, reasons=["target does not exist"])
        recipe = ctx.query_node(ctx.target).get("recipe")
        if not isinstance(recipe, dict):
            return CheckResult(
                passed=False, reasons=["target has no recipe dict"]
            )
        inputs = recipe.get("inputs")
        if not isinstance(inputs, list) or not inputs:
            return CheckResult(
                passed=False, reasons=["recipe has no non-empty inputs list"]
            )
        output_subtype = recipe.get("output_subtype")
        if not isinstance(output_subtype, str) or not output_subtype:
            return CheckResult(
                passed=False, reasons=["recipe missing output_subtype"]
            )
        return CheckResult(passed=True)

    def apply(self, ctx: MechanicContext) -> list[Mutation]:
        recipe = ctx.query_node(ctx.target).get("recipe") or {}
        inputs = recipe.get("inputs") or []
        output_subtype = recipe["output_subtype"]
        output_name = recipe.get("output_name") or output_subtype
        output_props: dict[str, Any] = {}
        raw_props = recipe.get("output_props")
        if isinstance(raw_props, dict):
            output_props = raw_props

        held = set(ctx.neighbors(ctx.actor, relation="holds"))
        for needed in inputs:
            if not isinstance(needed, str) or needed not in held:
                return _refuse_with_narrative(
                    ctx, ctx.actor, _NARRATIVE_MISSING_INPUT, target=ctx.target
                )

        new_id = ctx.claim_id(output_name)
        muts: list[Mutation] = []
        for needed in inputs:
            muts.append(ctx.remove_node(needed))
        muts.append(
            ctx.add_node(
                new_id,
                node_type="entity",
                subtype=output_subtype,
                **output_props,
            )
        )
        muts.append(ctx.add_edge(ctx.actor, new_id, relation="holds"))
        return muts
