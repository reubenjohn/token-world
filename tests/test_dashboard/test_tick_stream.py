"""Tests for the live tick stream panel (Plan 11-02 + §A7/A1/A2 redesign)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from token_world.dashboard.panels.tick_stream import (
    build_card,
    load_recent_tick_cards,
)


def test_build_card_exec_status() -> None:
    """A mechanic-matched tick yields ``exec`` status with mechanic_id detail."""
    tick = {
        "tick_id": "42",
        "timestamp_iso": "2026-04-14T00:00:05Z",
        "action_text": "open the chest",
        "matched_mechanic_id": "open_container",
        "observation_text": "The lid creaks.",
    }
    card = build_card(tick)
    assert card["tick_id"] == "42"
    assert card["status"] == "exec"
    assert card["status_detail"] == "open_container"
    assert card["action_text"] == "open the chest"
    assert card["observation"] == "The lid creaks."
    assert card["mechanic"] == "open_container"


def test_build_card_yield_status() -> None:
    tick = {
        "tick_id": "43",
        "yielded": True,
        "action_text": "summon a demigod",
    }
    card = build_card(tick)
    assert card["status"] == "yield"
    assert "operator" in card["status_detail"]


def test_build_card_refuse_status_with_reason() -> None:
    tick = {
        "tick_id": "44",
        "refused": True,
        "refusal_reason": "conservation_violation: hp cannot exceed max",
    }
    card = build_card(tick)
    assert card["status"] == "refuse"
    assert "conservation" in card["status_detail"]


def test_build_card_truncates_long_text() -> None:
    long_action = "a " * 200  # 400 chars
    long_obs = "b " * 200
    tick = {
        "tick_id": "45",
        "action_text": long_action,
        "observation_text": long_obs,
        "matched_mechanic_id": "noop",
    }
    card = build_card(tick)
    assert len(card["action_text"]) <= 80
    assert card["action_text"].endswith("...")
    assert len(card["observation"]) <= 120
    assert card["observation"].endswith("...")


def test_load_recent_tick_cards_empty(fake_universe: Path) -> None:
    """A universe with no ticks returns an empty list."""
    assert load_recent_tick_cards(fake_universe) == []


def test_load_recent_tick_cards_newest_first(fake_universe: Path, write_tick_dashboard) -> None:
    ticks_dir = fake_universe / "tick_summaries" / "ticks"
    write_tick_dashboard(ticks_dir, "1", action_text="one")
    write_tick_dashboard(ticks_dir, "2", action_text="two")
    write_tick_dashboard(ticks_dir, "10", action_text="ten")

    cards = load_recent_tick_cards(fake_universe)
    # Numeric sort — "10" is newer than "2".
    assert [c["tick_id"] for c in cards] == ["10", "2", "1"]
    assert cards[0]["action_text"] == "ten"


def test_load_recent_tick_cards_respects_max(fake_universe: Path, write_tick_dashboard) -> None:
    ticks_dir = fake_universe / "tick_summaries" / "ticks"
    for i in range(1, 15):
        write_tick_dashboard(ticks_dir, str(i), action_text=f"tick {i}")
    cards = load_recent_tick_cards(fake_universe, max_cards=5)
    assert len(cards) == 5
    # Highest-id ticks survive, newest-first.
    assert [c["tick_id"] for c in cards] == ["14", "13", "12", "11", "10"]


# ---------------------------------------------------------------------------
# SC-1a: actor_id field in build_card + filtering
# ---------------------------------------------------------------------------


def test_build_card_includes_actor_id_from_classified_action() -> None:
    tick = {
        "tick_id": "10",
        "classified_action": {"verb": "walk", "actor": "alice", "target": "forest"},
        "matched_mechanic_id": "move",
    }
    card = build_card(tick)
    assert card["actor_id"] == "alice"


def test_build_card_actor_id_empty_when_no_classified_action() -> None:
    tick = {"tick_id": "11", "action_text": "do something"}
    card = build_card(tick)
    assert card["actor_id"] == ""


def test_load_recent_tick_cards_filters_by_actor(fake_universe: Path, write_tick_dashboard) -> None:
    ticks_dir = fake_universe / "tick_summaries" / "ticks"
    write_tick_dashboard(ticks_dir, "1", classified_action={"actor": "alice"})
    write_tick_dashboard(ticks_dir, "2", classified_action={"actor": "bob"})
    write_tick_dashboard(ticks_dir, "3", classified_action={"actor": "alice"})
    cards = load_recent_tick_cards(fake_universe)
    alice_cards = [c for c in cards if c["actor_id"] == "alice"]
    bob_cards = [c for c in cards if c["actor_id"] == "bob"]
    assert len(alice_cards) == 2
    assert len(bob_cards) == 1


# ---------------------------------------------------------------------------
# §A7 scroll preservation — DOM reuse regression tests
# ---------------------------------------------------------------------------
#
# These tests use a lightweight fake ``ui`` object (not a real NiceGUI
# server) to verify the panel's *rendering contract* — specifically, that
# the poll handler never re-creates existing card elements on a no-op
# refresh. The real scroll-preservation guarantee rides on top of NiceGUI
# keeping the same element mounted client-side; here we assert the Python
# side of that contract.


class _FakeElement:
    """A minimal stand-in for a NiceGUI element.

    Tracks ``style``, ``children``, ``.text``, ``.value``, move targets,
    and classes so panel tests can make structural assertions without
    booting a real NiceGUI server.
    """

    def __init__(self, factory: str, *args: Any, **kwargs: Any) -> None:
        self.factory = factory
        self.args = args
        self.kwargs = kwargs
        self._classes: str = ""
        self._style: str = ""
        self._props: str = ""
        self.children: list[_FakeElement] = []
        self.text: str | None = args[0] if args else None
        self.value: Any = kwargs.get("value")
        self.moved_to: int | None = None

    def classes(self, s: str) -> _FakeElement:
        self._classes += " " + s
        return self

    def style(self, s: str) -> _FakeElement:
        self._style += s
        return self

    def props(self, s: str) -> _FakeElement:
        self._props += s
        return self

    def clear(self) -> None:
        self.children = []

    def move(self, *, target_index: int = -1) -> None:
        self.moved_to = target_index

    def remove(self, child: _FakeElement) -> None:
        if child in self.children:
            self.children.remove(child)

    # Context-manager protocol so the panel can use ``with outer: ...``.
    def __enter__(self) -> _FakeElement:
        _FakeUI._stack.append(self)
        return self

    def __exit__(self, *a: Any) -> None:
        _FakeUI._stack.pop()


class _FakeUI:
    """Module-level fake that panels import as ``from nicegui import ui``.

    Every factory (``ui.column``, ``ui.label``, ``ui.expansion``, ...)
    builds a :class:`_FakeElement`, appends it to the currently-open
    context, and returns it.
    """

    _stack: list[_FakeElement] = []
    _created: list[_FakeElement] = []
    timers: list[Any] = []

    @classmethod
    def _make(cls, factory: str, *args: Any, **kwargs: Any) -> _FakeElement:
        elem = _FakeElement(factory, *args, **kwargs)
        if cls._stack:
            cls._stack[-1].children.append(elem)
        cls._created.append(elem)
        return elem

    @classmethod
    def column(cls, *a: Any, **kw: Any) -> _FakeElement:
        return cls._make("column", *a, **kw)

    @classmethod
    def row(cls, *a: Any, **kw: Any) -> _FakeElement:
        return cls._make("row", *a, **kw)

    @classmethod
    def card(cls, *a: Any, **kw: Any) -> _FakeElement:
        return cls._make("card", *a, **kw)

    @classmethod
    def label(cls, text: str = "", *a: Any, **kw: Any) -> _FakeElement:
        return cls._make("label", text, *a, **kw)

    @classmethod
    def expansion(cls, text: str = "", *a: Any, **kw: Any) -> _FakeElement:
        return cls._make("expansion", text, *a, **kw)

    @classmethod
    def code(cls, *a: Any, **kw: Any) -> _FakeElement:
        return cls._make("code", *a, **kw)

    @classmethod
    def separator(cls, *a: Any, **kw: Any) -> _FakeElement:
        return cls._make("separator", *a, **kw)

    @classmethod
    def timer(cls, interval: float, cb: Any) -> Any:
        cls.timers.append((interval, cb))
        return object()


def _reset_fake_ui() -> None:
    _FakeUI._stack = []
    _FakeUI._created = []
    _FakeUI.timers = []


def _patch_ui(monkeypatch: Any) -> None:
    from nicegui import ui as real_ui

    for name in ("column", "row", "card", "label", "expansion", "code", "separator", "timer"):
        monkeypatch.setattr(real_ui, name, getattr(_FakeUI, name))


def _find_expansions(elem: _FakeElement) -> list[_FakeElement]:
    found: list[_FakeElement] = []
    if elem.factory == "expansion" and (elem.text or "").startswith("tick "):
        found.append(elem)
    for child in elem.children:
        found.extend(_find_expansions(child))
    return found


def test_poll_noop_reuses_mounted_cards(
    monkeypatch, fake_universe: Path, write_tick_dashboard
) -> None:
    """Calling the poll handler twice with no new ticks must not recreate cards.

    This is the §A7 regression — the pre-fix code ran ``outer.clear()``
    on every 2 s poll, nuking any open expansion's scroll position. The
    new contract: if the tick ID tuple is unchanged, *every* mounted
    card element must be the *same Python object* after the second poll.
    """
    _reset_fake_ui()
    _patch_ui(monkeypatch)

    ticks_dir = fake_universe / "tick_summaries" / "ticks"
    write_tick_dashboard(ticks_dir, "1", action_text="one")
    write_tick_dashboard(ticks_dir, "2", action_text="two")

    from token_world.dashboard.panels.tick_stream import mount_tick_stream_panel

    outer = mount_tick_stream_panel(fake_universe, "test-universe")

    assert _FakeUI.timers, "panel should install a poll timer"
    interval, cb = _FakeUI.timers[0]
    assert interval == 2.0

    first_snapshot = [id(e) for e in _find_expansions(outer)]
    assert len(first_snapshot) == 2, (
        f"expected 2 cards after initial render; got {len(first_snapshot)}"
    )

    # Second poll — no new ticks written. Must NOT recreate any card.
    cb()

    second_snapshot = [id(e) for e in _find_expansions(outer)]
    assert second_snapshot == first_snapshot, (
        "poll no-op rebuilt cards — scroll state would be lost"
    )


def test_poll_prepends_only_new_cards(
    monkeypatch, fake_universe: Path, write_tick_dashboard
) -> None:
    """When new ticks arrive, existing cards stay mounted; new cards prepend.

    Regression for §A7: if the poll handler notices new ticks but the
    existing window is still intact, only the new card elements should
    be created; existing elements must be the same Python objects.
    """
    _reset_fake_ui()
    _patch_ui(monkeypatch)

    ticks_dir = fake_universe / "tick_summaries" / "ticks"
    write_tick_dashboard(ticks_dir, "1", action_text="one")
    write_tick_dashboard(ticks_dir, "2", action_text="two")

    from token_world.dashboard.panels.tick_stream import mount_tick_stream_panel

    outer = mount_tick_stream_panel(fake_universe, "test-universe")

    cards_before = _find_expansions(outer)
    assert len(cards_before) == 2
    before_ids = {id(e) for e in cards_before}

    # New tick arrives.
    write_tick_dashboard(ticks_dir, "3", action_text="three")

    _, cb = _FakeUI.timers[0]
    cb()

    cards_after = _find_expansions(outer)
    # The two original cards must still be in the tree by Python identity.
    after_ids = {id(e) for e in cards_after}
    assert before_ids <= after_ids, "a previously-mounted card was re-created by the poll"
    new_cards = [e for e in cards_after if id(e) not in before_ids]
    assert len(new_cards) == 1
    assert "tick 3" in (new_cards[0].text or "")
    assert new_cards[0].moved_to == 0, "new card must be prepended with target_index=0"


# ---------------------------------------------------------------------------
# §A1 + §A2 structured expansion — sections + full-text observation
# ---------------------------------------------------------------------------


def _collect_label_texts(elem: _FakeElement) -> list[str]:
    out: list[str] = []
    if elem.factory == "label" and elem.text is not None:
        out.append(elem.text)
    for c in elem.children:
        out.extend(_collect_label_texts(c))
    return out


def test_expansion_renders_all_sections_and_full_observation(
    monkeypatch, fake_universe: Path, write_tick_dashboard
) -> None:
    """The expansion body must include every section label + the untruncated observation."""
    _reset_fake_ui()
    _patch_ui(monkeypatch)

    ticks_dir = fake_universe / "tick_summaries" / "ticks"
    long_observation = (
        "The thunder rolls across the valley.\n"
        "A cold wind bends the reeds.\n"
        "You feel the hair on your arms prickle, "
        "every nerve alive, every shadow moving."
    )
    write_tick_dashboard(
        ticks_dir,
        "42",
        action_text="listen to the storm",
        matched_mechanic_id="listen",
        classified_action={
            "verb": "listen",
            "actor": "mira",
            "target": "storm",
            "indirect_object": None,
        },
        observation_text=long_observation,
        mutations=[["mira", "mood", "calm", "alert"]],
        duration_ms=4321,
        classifier_in=10,
        classifier_out=5,
        observer_in=200,
        observer_out=80,
    )

    from token_world.dashboard.panels.tick_stream import mount_tick_stream_panel

    outer = mount_tick_stream_panel(fake_universe, "test-universe")

    all_texts = _collect_label_texts(outer)
    joined = "\n".join(all_texts)

    # Every required section header is present.
    for section in ("Classification", "Decision", "Mutations", "Observation", "Metadata"):
        assert section in joined, f"missing section header: {section} in:\n{joined}"

    # Full observation text rendered verbatim — newlines preserved, no
    # truncation ellipsis on the observation body.
    assert long_observation in joined, (
        "Observation text must render FULL + untruncated; found:\n" + joined
    )
    # Mutation is formatted as "target.prop: old -> new".
    assert "mira.mood" in joined
    # Raw JSON disclosure panel exists.
    assert any(
        e.factory == "expansion" and (e.text or "") == "Raw JSON" for e in _FakeUI._created
    ), "Raw JSON sub-expansion not found"
