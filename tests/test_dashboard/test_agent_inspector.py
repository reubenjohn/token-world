"""Tests for render_agent_inspector_sections() (SC-4/REQ-V12-DASHBOARD-08)."""

from __future__ import annotations

from token_world.dashboard.panels.agent_inspector import render_agent_inspector_sections
from token_world.inspect.agents import AgentSummary


def _make_summary(**kwargs) -> AgentSummary:
    defaults = dict(
        id="alice",
        personality=None,
        persona_text=None,
        memory_entries=[],
        active_lra=None,
        attention_state=None,
        other_properties={},
    )
    defaults.update(kwargs)
    return AgentSummary(**defaults)


def _section(sections, title: str) -> dict:
    for s in sections:
        if s["title"] == title:
            return s
    raise AssertionError(f"Section '{title}' not found in {[s['title'] for s in sections]}")


# ---------------------------------------------------------------------------
# test_identity_section_with_personality
# ---------------------------------------------------------------------------


def test_identity_section_with_personality() -> None:
    summary = _make_summary(personality={"name": "Alice", "age": 25, "trait": "curious"})
    sections = render_agent_inspector_sections(summary, [])
    identity = _section(sections, "Identity")
    assert any("personality keys:" in item for item in identity["items"])


# ---------------------------------------------------------------------------
# test_identity_section_with_persona_text
# ---------------------------------------------------------------------------


def test_identity_section_with_persona_text() -> None:
    summary = _make_summary(persona_text="Alice is a brave explorer.\nShe explores dungeons.")
    sections = render_agent_inspector_sections(summary, [])
    identity = _section(sections, "Identity")
    # persona text (first line, truncated) should appear
    assert any("Alice is a brave explorer" in item for item in identity["items"])


# ---------------------------------------------------------------------------
# test_location_section_present
# ---------------------------------------------------------------------------


def test_location_section_present() -> None:
    summary = _make_summary(other_properties={"located_in": "cottage"})
    sections = render_agent_inspector_sections(summary, [])
    location = _section(sections, "Location")
    assert any("cottage" in item for item in location["items"])


# ---------------------------------------------------------------------------
# test_location_section_absent
# ---------------------------------------------------------------------------


def test_location_section_absent() -> None:
    summary = _make_summary()
    sections = render_agent_inspector_sections(summary, [])
    location = _section(sections, "Location")
    assert "(unknown)" in location["items"]


# ---------------------------------------------------------------------------
# test_memory_section_truncates_to_10
# ---------------------------------------------------------------------------


def test_memory_section_truncates_to_10() -> None:
    entries = [f"memory {i}" for i in range(15)]
    summary = _make_summary(memory_entries=entries)
    sections = render_agent_inspector_sections(summary, [])
    memory = _section(sections, "Memory")
    assert len(memory["items"]) == 10
    # Should be the LAST 10
    assert memory["items"][0] == "memory 5"
    assert memory["items"][-1] == "memory 14"


# ---------------------------------------------------------------------------
# test_lra_section_active
# ---------------------------------------------------------------------------


def test_lra_section_active() -> None:
    summary = _make_summary(
        active_lra={"action_text": "sleeping", "turns_elapsed": 3, "turns_total": 8}
    )
    sections = render_agent_inspector_sections(summary, [])
    lra = _section(sections, "Active LRA")
    assert any("sleeping" in item and "3/8" in item for item in lra["items"])


# ---------------------------------------------------------------------------
# test_lra_section_none
# ---------------------------------------------------------------------------


def test_lra_section_none() -> None:
    summary = _make_summary()
    sections = render_agent_inspector_sections(summary, [])
    lra = _section(sections, "Active LRA")
    assert "(none)" in lra["items"]


# ---------------------------------------------------------------------------
# test_attention_section
# ---------------------------------------------------------------------------


def test_attention_section() -> None:
    summary = _make_summary(attention_state={"focus": "door", "mood": "curious"})
    sections = render_agent_inspector_sections(summary, [])
    attn = _section(sections, "Attention")
    assert any("focus: door" in item for item in attn["items"])
    assert any("mood: curious" in item for item in attn["items"])


# ---------------------------------------------------------------------------
# test_recent_actions_empty
# ---------------------------------------------------------------------------


def test_recent_actions_empty() -> None:
    summary = _make_summary()
    sections = render_agent_inspector_sections(summary, [])
    recent = _section(sections, "Recent Actions")
    assert "(none)" in recent["items"]


# ---------------------------------------------------------------------------
# test_all_sections_present
# ---------------------------------------------------------------------------


def test_all_sections_present() -> None:
    summary = _make_summary()
    sections = render_agent_inspector_sections(summary, ["look around"])
    titles = [s["title"] for s in sections]
    assert "Identity" in titles
    assert "Location" in titles
    assert "Memory" in titles
    assert "Active LRA" in titles
    assert "Attention" in titles
    assert "Recent Actions" in titles
    assert len(sections) == 6
