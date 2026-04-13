"""Tests for TickSummaryWriter and build_tick_summary (Plan 05-07).

TDD: written before the implementation. Tests import from
token_world.engine.summary_writer and token_world.engine (exported names).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from token_world.engine import TickSummaryWriter, build_tick_summary
from token_world.engine.models import ExecuteDecision, RefuseDecision, TickSummary, YieldDecision
from token_world.graph.models import Mutation
from token_world.mechanic.protocol import CheckResult
from token_world.mechanic.trace import ExecutionTrace, TraceNode

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mutation(
    target: str = "rock_1",
    prop: str = "weight",
    old: object = None,
    new: object = 5,
) -> Mutation:
    return Mutation(type="set_property", target=target, property=prop, old_value=old, new_value=new)


def _make_trace_node(
    mutations: list[Mutation], children: list[TraceNode] | None = None
) -> TraceNode:
    return TraceNode(
        mechanic_id="test_mechanic",
        actor="alice",
        target="rock_1",
        check_result=CheckResult(passed=True),
        mutations=mutations,
        children=children or [],
    )


def _make_trace(
    mutations: list[Mutation], children: list[TraceNode] | None = None
) -> ExecutionTrace:
    root = _make_trace_node(mutations, children)
    return ExecutionTrace(root=root, total_mechanics_executed=1, max_depth_reached=1)


def _default_execute_summary(
    tick_id: str = "42",
    mechanic_id: str = "pickup",
    mutations: list[Mutation] | None = None,
) -> TickSummary:
    """Build an execute-path TickSummary for use in writer tests."""
    trace = _make_trace(mutations or [_make_mutation()])
    return build_tick_summary(
        tick_id=tick_id,
        action_text="pick up the rock",
        decision=ExecuteDecision(mechanic_id=mechanic_id),
        classified_action={"verb": "pickup", "actor": "alice", "target": "rock_1"},
        trace=trace,
        observation_text="You pick up the rock.",
        duration_ms=120,
        classifier_input_tokens=100,
        classifier_output_tokens=20,
        observer_input_tokens=200,
        observer_output_tokens=50,
    )


# ---------------------------------------------------------------------------
# Writer tests
# ---------------------------------------------------------------------------


class TestTickSummaryWriter:
    """Tests for TickSummaryWriter.write()."""

    def test_writer_creates_file_at_expected_path(self, tmp_path: Path) -> None:
        """Write creates tick_{tick_id}.json at the expected location."""
        writer = TickSummaryWriter()
        summary = _default_execute_summary(tick_id="42")
        writer.write(summary, tmp_path)
        expected = tmp_path / "tick_summaries" / "ticks" / "tick_42.json"
        assert expected.exists()

    def test_writer_creates_ticks_subdir_when_missing(self, tmp_path: Path) -> None:
        """Directory tick_summaries/ticks/ is created if it doesn't exist."""
        writer = TickSummaryWriter()
        # Start with a completely empty tmp_path — no tick_summaries dir at all
        assert not (tmp_path / "tick_summaries").exists()
        summary = _default_execute_summary(tick_id="1")
        writer.write(summary, tmp_path)
        assert (tmp_path / "tick_summaries" / "ticks").is_dir()

    def test_written_file_is_valid_json_with_schema_version_1(self, tmp_path: Path) -> None:
        """The written file must be parseable JSON with schema_version == 1."""
        writer = TickSummaryWriter()
        summary = _default_execute_summary(tick_id="10")
        writer.write(summary, tmp_path)
        path = tmp_path / "tick_summaries" / "ticks" / "tick_10.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_version"] == 1

    def test_written_file_contains_all_d20_fields(self, tmp_path: Path) -> None:
        """Written file must contain every field listed in D-20."""
        writer = TickSummaryWriter()
        summary = _default_execute_summary(tick_id="20")
        writer.write(summary, tmp_path)
        path = tmp_path / "tick_summaries" / "ticks" / "tick_20.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        required_keys = {
            "schema_version",
            "tick_id",
            "timestamp_iso",
            "action_text",
            "classified_action",
            "matched_mechanic_id",
            "yielded",
            "refused",
            "refusal_reason",
            "mutations",
            "observation_text",
            "duration_ms",
            "llm_tokens_by_stage",
            "llm_cost_usd_by_stage",
        }
        assert required_keys <= set(data.keys())

    def test_idempotent_overwrite_same_tick_id(self, tmp_path: Path) -> None:
        """Writing the same tick_id twice overwrites — last write wins."""
        writer = TickSummaryWriter()
        summary1 = build_tick_summary(
            tick_id="99",
            action_text="first action",
            decision=ExecuteDecision(mechanic_id="m1"),
            classified_action=None,
            trace=_make_trace([]),
            observation_text=None,
            duration_ms=10,
        )
        summary2 = build_tick_summary(
            tick_id="99",
            action_text="second action",
            decision=ExecuteDecision(mechanic_id="m2"),
            classified_action=None,
            trace=_make_trace([]),
            observation_text="Different.",
            duration_ms=20,
        )
        writer.write(summary1, tmp_path)
        writer.write(summary2, tmp_path)
        path = tmp_path / "tick_summaries" / "ticks" / "tick_99.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["action_text"] == "second action"

    def test_atomic_write_no_partial_files(self, tmp_path: Path) -> None:
        """After a successful write, no .tmp files remain in tick_summaries/ticks/."""
        writer = TickSummaryWriter()
        summary = _default_execute_summary(tick_id="55")
        writer.write(summary, tmp_path)
        ticks_dir = tmp_path / "tick_summaries" / "ticks"
        tmp_files = list(ticks_dir.glob("*.tmp*"))
        assert tmp_files == [], f"Unexpected tmp files: {tmp_files}"

    def test_writer_returns_path(self, tmp_path: Path) -> None:
        """write() returns a Path whose .name matches the expected filename."""
        writer = TickSummaryWriter()
        summary = _default_execute_summary(tick_id="77")
        result = writer.write(summary, tmp_path)
        assert isinstance(result, Path)
        assert result.name == "tick_77.json"

    def test_round_trip_pydantic_validation(self, tmp_path: Path) -> None:
        """Re-parsing the written file via TickSummary.model_validate() must succeed."""
        writer = TickSummaryWriter()
        summary = _default_execute_summary(tick_id="88")
        path = writer.write(summary, tmp_path)
        text = path.read_text(encoding="utf-8")
        # Should not raise
        reparsed = TickSummary.model_validate(json.loads(text))
        assert reparsed.tick_id == "88"
        assert reparsed.schema_version == 1


# ---------------------------------------------------------------------------
# build_tick_summary — path tests
# ---------------------------------------------------------------------------


class TestBuildTickSummaryExecutePath:
    """Tests for build_tick_summary on the EXECUTE path."""

    def test_execute_path_basic(self) -> None:
        """ExecuteDecision: matched_mechanic_id set, yielded/refused False."""
        m1 = _make_mutation("rock_1", "weight", None, 5)
        m2 = _make_mutation("alice", "carrying", None, ["rock_1"])
        trace = _make_trace([m1, m2])
        summary = build_tick_summary(
            tick_id="exec-1",
            action_text="pick up rock",
            decision=ExecuteDecision(mechanic_id="pickup"),
            classified_action={"verb": "pickup", "actor": "alice"},
            trace=trace,
            observation_text="You pick up the rock.",
            duration_ms=200,
        )
        assert summary.matched_mechanic_id == "pickup"
        assert summary.yielded is False
        assert summary.refused is False
        assert summary.mutations["count"] == 2
        assert len(summary.mutations["list"]) == 2

    def test_flattens_trace_children(self) -> None:
        """Mutations from root + children are all counted."""
        m1 = _make_mutation("rock_1", "weight", None, 5)
        m2 = _make_mutation("bag_1", "contents", None, [])
        m3 = _make_mutation("bag_1", "contents", [], ["rock_1"])
        child_node = _make_trace_node([m2, m3])
        trace = _make_trace([m1], children=[child_node])
        summary = build_tick_summary(
            tick_id="chain-1",
            action_text="put rock in bag",
            decision=ExecuteDecision(mechanic_id="store_item"),
            classified_action=None,
            trace=trace,
            observation_text="Done.",
            duration_ms=50,
        )
        assert summary.mutations["count"] == 3

    def test_mutations_serialise_as_4_tuple(self) -> None:
        """Each mutation entry in mutations.list is [target, property, old, new]."""
        mut = _make_mutation("node_x", "hp", 10, 5)
        trace = _make_trace([mut])
        summary = build_tick_summary(
            tick_id="mut-1",
            action_text="attack",
            decision=ExecuteDecision(mechanic_id="combat"),
            classified_action=None,
            trace=trace,
            observation_text=None,
            duration_ms=30,
        )
        entry = summary.mutations["list"][0]
        assert len(entry) == 4
        assert entry == ["node_x", "hp", 10, 5]


class TestBuildTickSummaryYieldPath:
    """Tests for build_tick_summary on the YIELD path."""

    def test_yield_path(self) -> None:
        """YieldDecision: yielded=True, all mechanic/observation/refusal fields None."""
        decision = YieldDecision(  # type: ignore[arg-type]
            classified={"verb": "look", "actor": "alice", "target": None, "params": {}}
        )
        summary = build_tick_summary(
            tick_id="yield-1",
            action_text="look around",
            decision=decision,
            classified_action={"verb": "look", "actor": "alice"},
            trace=None,
            observation_text=None,
            duration_ms=10,
        )
        assert summary.yielded is True
        assert summary.matched_mechanic_id is None
        assert summary.refused is False
        assert summary.refusal_reason is None
        assert summary.mutations == {"count": 0, "list": []}


class TestBuildTickSummaryRefusePath:
    """Tests for build_tick_summary on the REFUSE path."""

    def test_refuse_path(self) -> None:
        """RefuseDecision: refused=True, reason_code forwarded, mechanic None."""
        decision = RefuseDecision(reason_code="no_viable_action", details={"raw": "????"})
        summary = build_tick_summary(
            tick_id="refuse-1",
            action_text="flibble gribble",
            decision=decision,
            classified_action=None,
            trace=None,
            observation_text=None,
            duration_ms=5,
        )
        assert summary.refused is True
        assert summary.yielded is False
        assert summary.refusal_reason == "no_viable_action"
        assert summary.matched_mechanic_id is None


# ---------------------------------------------------------------------------
# Cost accounting tests
# ---------------------------------------------------------------------------


class TestCostAccounting:
    """Tests for per-stage cost computation via model-rate constants."""

    def _base_kwargs(self, **overrides) -> dict:
        kw = dict(
            tick_id="cost-test",
            action_text="any",
            decision=ExecuteDecision(mechanic_id="m"),
            classified_action=None,
            trace=_make_trace([]),
            observation_text=None,
            duration_ms=1,
        )
        kw.update(overrides)
        return kw

    def test_classifier_cost_uses_haiku_rates(self) -> None:
        """1M input tokens at Haiku input rate == $1.00 per million."""
        summary = build_tick_summary(
            **self._base_kwargs(classifier_input_tokens=1_000_000, classifier_output_tokens=0)
        )
        assert summary.llm_cost_usd_by_stage["classifier"] == pytest.approx(1.00)

    def test_observer_cost_uses_sonnet_rates(self) -> None:
        """1M output tokens at Sonnet output rate == $15.00 per million."""
        summary = build_tick_summary(
            **self._base_kwargs(observer_input_tokens=0, observer_output_tokens=1_000_000)
        )
        assert summary.llm_cost_usd_by_stage["observer"] == pytest.approx(15.00)

    def test_zero_token_usage_yields_zero_cost(self) -> None:
        """Default token counts (0) produce 0.0 cost for both stages."""
        summary = build_tick_summary(**self._base_kwargs())
        assert summary.llm_cost_usd_by_stage["classifier"] == 0.0
        assert summary.llm_cost_usd_by_stage["observer"] == 0.0

    def test_tokens_by_stage_structure(self) -> None:
        """llm_tokens_by_stage has classifier and observer keys with in/out sub-keys."""
        summary = build_tick_summary(
            **self._base_kwargs(
                classifier_input_tokens=100,
                classifier_output_tokens=20,
                observer_input_tokens=200,
                observer_output_tokens=50,
            )
        )
        assert summary.llm_tokens_by_stage["classifier"] == {"in": 100, "out": 20}
        assert summary.llm_tokens_by_stage["observer"] == {"in": 200, "out": 50}


# ---------------------------------------------------------------------------
# Timestamp format test
# ---------------------------------------------------------------------------


class TestTimestamp:
    def test_timestamp_iso_format_z_suffix(self) -> None:
        """timestamp_iso must end with 'Z' and be exactly 20 characters."""
        summary = build_tick_summary(
            tick_id="ts-1",
            action_text="test",
            decision=ExecuteDecision(mechanic_id="m"),
            classified_action=None,
            trace=_make_trace([]),
            observation_text=None,
            duration_ms=1,
        )
        assert summary.timestamp_iso.endswith("Z")
        assert len(summary.timestamp_iso) == 20, (
            f"Expected 20 chars (YYYY-MM-DDTHH:MM:SSZ), got {len(summary.timestamp_iso)}: "
            f"{summary.timestamp_iso!r}"
        )
