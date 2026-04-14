"""Tests for :mod:`token_world.dashboard.panels.active_yield`.

Exercises the pure-logic surface (``load_pending_yields`` +
``format_banner_text``) without booting NiceGUI. A smoke test on the
``mount_active_yield_banner`` binding is deferred to the integration
tests (``test_dashboard/test_integration.py``), which already Playwright-
drive the full app.
"""

from __future__ import annotations

import json
from pathlib import Path

from token_world.dashboard.panels.active_yield import (
    format_banner_text,
    load_pending_yields,
)
from token_world.inspect.yields import PendingYield


def _write_yield_file(
    inbox: Path,
    tick_id: str,
    *,
    verb: str = "pickup",
    actor: str = "alice",
    target: str | None = "rock_1",
    action_text: str = "pick up the rock",
    reason: str = "no_mechanic_for_action",
) -> Path:
    inbox.mkdir(parents=True, exist_ok=True)
    payload = {
        "tick_id": tick_id,
        "universe_path": str(inbox.parent),
        "schema_version": 1,
        "reason": reason,
        "action_text": action_text,
        "classified_action": {
            "verb": verb,
            "actor": actor,
            "target": target,
            "params": {},
        },
        "actor_state": {},
        "candidate_mechanic_ids": [],
    }
    path = inbox / f"{tick_id}.yield.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# load_pending_yields()
# ---------------------------------------------------------------------------


def test_load_pending_no_inbox(fake_universe: Path) -> None:
    """Missing operator_inbox returns an empty list (graceful)."""
    assert load_pending_yields(fake_universe) == []


def test_load_pending_one_yield(fake_universe: Path) -> None:
    inbox = fake_universe / "operator_inbox"
    _write_yield_file(inbox, "42")
    pending = load_pending_yields(fake_universe)
    assert len(pending) == 1
    assert pending[0].tick_id == "42"


def test_load_pending_resolved_hidden(fake_universe: Path) -> None:
    """A ``.resolved`` sibling removes the yield from the pending list."""
    inbox = fake_universe / "operator_inbox"
    _write_yield_file(inbox, "42")
    assert len(load_pending_yields(fake_universe)) == 1
    (inbox / "42.resolved").write_text('{"mechanic_id":"pickup_v1"}', encoding="utf-8")
    assert load_pending_yields(fake_universe) == []


def test_load_pending_rejected_hidden(fake_universe: Path) -> None:
    """A ``.rejected`` sibling removes the yield from the pending list."""
    inbox = fake_universe / "operator_inbox"
    _write_yield_file(inbox, "42")
    (inbox / "42.rejected").write_text('{"reason":"incoherent"}', encoding="utf-8")
    assert load_pending_yields(fake_universe) == []


def test_load_pending_corrupt_universe_returns_empty(tmp_path: Path) -> None:
    """Nonexistent path must not raise — banner degrades gracefully."""
    bogus = tmp_path / "nope" / "does_not_exist"
    assert load_pending_yields(bogus) == []


# ---------------------------------------------------------------------------
# format_banner_text()
# ---------------------------------------------------------------------------


def test_format_banner_empty_list() -> None:
    assert format_banner_text([]) == ""


def test_format_banner_single_yield() -> None:
    py = PendingYield(
        tick_id="42",
        verb="pickup",
        actor="alice",
        target="rock_1",
        action_text="pick up the rock",
        hint="no_mechanic_for_action",
        mtime_iso="2026-04-14T00:00:00+00:00",
        path="/tmp/42.yield.json",
    )
    text = format_banner_text([py])
    assert "Pending yield on tick 42" in text
    assert "pickup alice -> rock_1" in text
    assert "hint: no_mechanic_for_action" in text
    assert not text.startswith("[")  # no "+N more" prefix with just one


def test_format_banner_multiple_yields_shows_count_and_latest() -> None:
    older = PendingYield(
        tick_id="10",
        verb="speak",
        actor="bob",
        target=None,
        action_text="say hi",
        hint="no_mechanic_for_action",
        mtime_iso="2026-04-14T00:00:00+00:00",
        path="/tmp/10.yield.json",
    )
    newer = PendingYield(
        tick_id="42",
        verb="pickup",
        actor="alice",
        target="rock_1",
        action_text="pick up the rock",
        hint="no_mechanic_for_action",
        mtime_iso="2026-04-14T01:00:00+00:00",
        path="/tmp/42.yield.json",
    )
    text = format_banner_text([older, newer])  # mtime-ascending
    assert text.startswith("[+1 more]")
    assert "Pending yield on tick 42" in text  # most recent highlighted
    assert "pickup alice -> rock_1" in text


def test_format_banner_handles_none_target() -> None:
    py = PendingYield(
        tick_id="7",
        verb="shout",
        actor="alice",
        target=None,
        action_text="shout!",
        hint="no_mechanic_for_action",
        mtime_iso="2026-04-14T00:00:00+00:00",
        path="/tmp/7.yield.json",
    )
    text = format_banner_text([py])
    # Targetless verbs render as "->" followed by a dash placeholder.
    assert "shout alice -> -" in text


# ---------------------------------------------------------------------------
# mount_active_yield_banner() — exercised through create_app
# ---------------------------------------------------------------------------


def test_banner_module_imports() -> None:
    """The module imports cleanly (including NiceGUI)."""
    from token_world.dashboard.panels import active_yield

    assert hasattr(active_yield, "mount_active_yield_banner")


def test_banner_no_yield_hidden(fake_universe: Path) -> None:
    """With no pending yields, the banner's visible state is False after mount."""
    from nicegui import ui

    from token_world.dashboard.panels.active_yield import mount_active_yield_banner

    parent = ui.column()
    mount_active_yield_banner(fake_universe, parent)
    # The banner is the first child of `parent`; `visible=False` by contract.
    children = list(parent.default_slot.children)
    assert len(children) == 1, "banner should be mounted as a single child"
    banner = children[0]
    assert banner.visible is False


def test_banner_one_pending_visible(fake_universe: Path) -> None:
    """With a pending yield, the banner becomes visible with the correct text."""
    from nicegui import ui

    from token_world.dashboard.panels.active_yield import mount_active_yield_banner

    _write_yield_file(fake_universe / "operator_inbox", "42")
    parent = ui.column()
    mount_active_yield_banner(fake_universe, parent)
    children = list(parent.default_slot.children)
    banner = children[0]
    assert banner.visible is True
    # The inner label is the banner's first child.
    label = list(banner.default_slot.children)[0]
    assert "Pending yield on tick 42" in label.text
    assert "pickup alice -> rock_1" in label.text


def test_banner_resolved_hides(fake_universe: Path) -> None:
    """A resolved yield should cause the banner to hide on the next poll.

    Because ``ui.timer`` runs on NiceGUI's async loop (not directly pokeable
    in a unit test), we call the module-level refresh by re-invoking
    ``mount_active_yield_banner`` with the post-resolve state — i.e. we are
    asserting the *invariant* (no pending → hidden), not the timer plumbing.
    """
    from nicegui import ui

    from token_world.dashboard.panels.active_yield import mount_active_yield_banner

    inbox = fake_universe / "operator_inbox"
    _write_yield_file(inbox, "42")
    (inbox / "42.resolved").write_text('{"mechanic_id":"pickup_v1"}', encoding="utf-8")
    parent = ui.column()
    mount_active_yield_banner(fake_universe, parent)
    banner = list(parent.default_slot.children)[0]
    assert banner.visible is False
