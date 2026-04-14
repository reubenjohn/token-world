"""Agent inspector (``token-world agents <slug> [--id X]``).

Reads agent-typed nodes from the universe's graph and surfaces:

- Personality bundle / persona text (when stored on the node)
- Rolling memory entries (when stored on the node)
- Active long-running action (``current_long_action``)
- Attention state nested inside the LRA payload (D-12)
- Generic property dump (every other property on the node)

Without ``--id``, returns one row per agent. With ``--id alice``,
returns the full property dict for that single agent.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AgentSummary:
    """Per-agent summary returned by ``aggregate``."""

    id: str
    personality: dict[str, Any] | None = None
    persona_text: str | None = None
    memory_entries: list[Any] = field(default_factory=list)
    active_lra: dict[str, Any] | None = None
    attention_state: dict[str, Any] | None = None
    other_properties: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentsReport:
    """Aggregate report for one or more agents."""

    slug: str
    agents: list[AgentSummary] = field(default_factory=list)
    not_found_id: str | None = None  # set when --id was passed but missing


def _split_props(props: dict[str, Any]) -> AgentSummary:
    """Bucket a node's property dict into the AgentSummary fields."""
    summary = AgentSummary(id="")  # caller fills in id
    consumed: set[str] = set()

    if "personality" in props and isinstance(props["personality"], dict):
        summary.personality = props["personality"]
        consumed.add("personality")

    for key in ("persona_text", "persona", "system_prompt"):
        if key in props and isinstance(props[key], str):
            summary.persona_text = props[key]
            consumed.add(key)
            break

    for key in ("memory", "rolling_memory", "memory_entries"):
        if key in props and isinstance(props[key], list):
            summary.memory_entries = list(props[key])
            consumed.add(key)
            break

    lra = props.get("current_long_action")
    if isinstance(lra, dict):
        summary.active_lra = lra
        consumed.add("current_long_action")
        payload = lra.get("payload")
        if isinstance(payload, dict) and isinstance(payload.get("attention_state"), dict):
            summary.attention_state = payload["attention_state"]

    summary.other_properties = {
        k: v for k, v in props.items() if k not in consumed and k not in {"type"}
    }
    return summary


def aggregate(
    universe_dir: Path,
    *,
    slug: str,
    agent_id: str | None = None,
) -> AgentsReport:
    """Build an :class:`AgentsReport`.

    Args:
        universe_dir: Universe root directory.
        slug: Universe slug (display only).
        agent_id: When set, return only that single agent (or
            ``not_found_id`` if it doesn't exist).
    """
    report = AgentsReport(slug=slug)
    db_path = universe_dir / "universe.db"
    if not db_path.is_file():
        return report

    from token_world.graph import KnowledgeGraph

    kg = KnowledgeGraph(db_path=db_path)
    try:
        kg.load()
    except (ValueError, OSError):
        return report

    agent_ids = sorted(kg.nodes(type="agent"))
    if agent_id is not None:
        if agent_id not in agent_ids:
            report.not_found_id = agent_id
            return report
        agent_ids = [agent_id]

    for aid in agent_ids:
        props = kg.query(aid)
        summary = _split_props(dict(props))
        summary.id = aid
        report.agents.append(summary)
    return report


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_table(report: AgentsReport) -> str:
    out: list[str] = []
    out.append(f"=== Agents: {report.slug} ===")
    if report.not_found_id:
        out.append(f"(no agent with id={report.not_found_id!r})")
        return "\n".join(out) + "\n"
    if not report.agents:
        out.append("(no agents in graph)")
        return "\n".join(out) + "\n"

    for agent in report.agents:
        out.append("")
        out.append(f"  {agent.id}")
        if agent.personality is not None:
            out.append(f"    personality keys: {sorted(agent.personality.keys())}")
        if agent.persona_text is not None:
            preview = agent.persona_text.strip().split("\n", 1)[0]
            if len(preview) > 80:
                preview = preview[:77] + "..."
            out.append(f"    persona:    {preview}")
        out.append(f"    memory:     {len(agent.memory_entries)} entries")
        if agent.active_lra:
            action = str(agent.active_lra.get("action_text", ""))[:80]
            elapsed = agent.active_lra.get("turns_elapsed", 0)
            total = agent.active_lra.get("turns_total")
            duration = f"{elapsed}/{total}" if total is not None else f"{elapsed}/-"
            out.append(f"    LRA:        [{duration}] {action}")
        else:
            out.append("    LRA:        (none)")
        if agent.attention_state:
            out.append(f"    attention:  {agent.attention_state}")
        if agent.other_properties:
            keys = sorted(agent.other_properties.keys())
            out.append(f"    props:      {keys}")
    return "\n".join(out) + "\n"


def render_json(report: AgentsReport, *, indent: int | None = 2) -> str:
    payload: dict[str, Any] = {
        "slug": report.slug,
        "not_found_id": report.not_found_id,
        "agents": [asdict(a) for a in report.agents],
    }
    return json.dumps(payload, indent=indent, sort_keys=True, default=str) + "\n"
