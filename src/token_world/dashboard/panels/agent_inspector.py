"""Agent inspector panel for the graph canvas drawer (REQ-V12-DASHBOARD-08).

Renders an AgentSummary as structured labelled sections. The framework-agnostic
render_agent_inspector_sections() returns plain dicts for testing; mount_agent_inspector()
renders those into NiceGUI ui.expansion() elements.

Section layout (CONTEXT.md §SC-4):
1. Identity: id, personality summary (key names) or persona_text first line
2. Location: located_in property value or "(unknown)"
3. Memory: last 10 entries from memory_entries
4. Active LRA: action_text + turns_elapsed/turns_total
5. Attention: key-value pairs from attention_state
6. Recent Actions: last 10 action_texts from tick summaries
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from token_world.inspect.agents import AgentSummary, _split_props

if TYPE_CHECKING:
    pass

__all__ = ["render_agent_inspector_sections", "mount_agent_inspector", "agent_summary_from_props"]


def agent_summary_from_props(node_id: str, properties: dict[str, Any]) -> AgentSummary:
    """Build an AgentSummary from a raw node property dict (from graph_canvas snapshot)."""
    summary = _split_props(dict(properties))
    summary.id = node_id
    return summary


def render_agent_inspector_sections(
    agent_summary: AgentSummary,
    recent_actions: list[str],
) -> list[dict[str, Any]]:
    """Return [{title: str, items: list[str]}] — framework-agnostic for tests.

    T-17-03-02: memory capped at 10; T-17-03-01: persona truncated to 100 chars.

    Args:
        agent_summary: Populated AgentSummary from the knowledge graph node.
        recent_actions: Action texts from recent ticks for this agent (pre-sorted).

    Returns:
        A list of exactly 6 section dicts in canonical order.
    """
    sections: list[dict[str, Any]] = []

    # 1. Identity
    identity_items: list[str] = [f"id: {agent_summary.id}"]
    if agent_summary.personality is not None:
        identity_items.append(f"personality keys: {sorted(agent_summary.personality.keys())}")
    elif agent_summary.persona_text is not None:
        # Truncate to first line, max 100 chars (T-17-03-01)
        preview = agent_summary.persona_text.strip().split("\n", 1)[0][:100]
        identity_items.append(f"persona: {preview}")
    sections.append({"title": "Identity", "items": identity_items})

    # 2. Location
    located_in = agent_summary.other_properties.get("located_in")
    location_items = [f"located_in: {located_in}"] if located_in else ["(unknown)"]
    sections.append({"title": "Location", "items": location_items})

    # 3. Memory (last 10 — T-17-03-02)
    entries = agent_summary.memory_entries[-10:] if agent_summary.memory_entries else []
    if entries:
        memory_items = [str(e) if not isinstance(e, str) else e for e in entries]
    else:
        memory_items = ["(no memory)"]
    sections.append({"title": "Memory", "items": memory_items})

    # 4. Active LRA
    if agent_summary.active_lra:
        action = str(agent_summary.active_lra.get("action_text", ""))
        elapsed = agent_summary.active_lra.get("turns_elapsed", 0)
        total = agent_summary.active_lra.get("turns_total")
        duration = f"{elapsed}/{total}" if total is not None else f"{elapsed}/-"
        lra_items = [f"{action} [{duration}]"]
    else:
        lra_items = ["(none)"]
    sections.append({"title": "Active LRA", "items": lra_items})

    # 5. Attention
    if agent_summary.attention_state:
        attn_items = [f"{k}: {v}" for k, v in agent_summary.attention_state.items()]
    else:
        attn_items = ["(none)"]
    sections.append({"title": "Attention", "items": attn_items})

    # 6. Recent Actions (last 10)
    action_items = list(recent_actions[-10:]) if recent_actions else ["(none)"]
    sections.append({"title": "Recent Actions", "items": action_items})

    return sections


def mount_agent_inspector(
    agent_summary: AgentSummary,
    recent_actions: list[str],
    container: Any,
) -> None:
    """Render sections into a NiceGUI container using ui.expansion() per section.

    §A7: Only called from _on_node_click (user-driven), never from poll handler.
    """
    from nicegui import ui

    container.clear()
    with container:
        ui.label(f"Agent: {agent_summary.id}").classes(
            "text-base font-semibold text-slate-100 mb-2"
        )
        for section in render_agent_inspector_sections(agent_summary, recent_actions):
            with ui.expansion(section["title"], value=True).classes("w-full"):
                for item in section["items"]:
                    ui.label(item).classes("text-xs font-mono text-slate-300 py-0.5")
