"""conservation.yaml template — declares conserved properties for the engine.

Empty by default per D-16: universes opt-in by listing property names.
Loaded by ``ConservationChecker.from_yaml`` at engine init.
"""

from __future__ import annotations

CONSERVATION_YAML_TEMPLATE = """\
# conservation.yaml — declare conserved properties (D-16, SIM-08).
#
# Empty by default. The engine enforces no conservation when this list is empty.
# To opt-in, list property names whose net change across a tick MUST sum to zero:
#
#     conserved_properties:
#       - coin
#       - health
#       - mass
#
# If a tick's mutations would create or destroy a conserved property's net total,
# the engine rolls back the tick and refuses with a conservation_violation narrative.
conserved_properties: []
"""


def render_conservation_yaml() -> str:
    """Return the conservation.yaml template text (no parameters)."""
    return CONSERVATION_YAML_TEMPLATE
