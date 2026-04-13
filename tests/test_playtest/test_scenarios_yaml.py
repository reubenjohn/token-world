"""Tests for Scenario YAML loader and InjectionSampler (Task 1, RED phase)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Scenario loading tests
# ---------------------------------------------------------------------------


def test_scenario_loads_from_yaml_file(tmp_path: Path) -> None:
    """Test 1: Scenario.load returns a Scenario with matching fields."""
    from token_world.playtest import Scenario

    data = {
        "name": "basic_exploration",
        "description": "Agent explores a starting room",
        "adversarial_rate": 0.1,
        "seed": 42,
        "turns": [
            {"action": "look around"},
            {"inject": "nonsense"},
        ],
    }
    p = tmp_path / "scenario.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")

    scenario = Scenario.load(p)
    assert scenario.name == "basic_exploration"
    assert scenario.description == "Agent explores a starting room"
    assert scenario.adversarial_rate == 0.1
    assert scenario.seed == 42
    assert len(scenario.turns) == 2


def test_scenario_rejects_invalid_inject_type(tmp_path: Path) -> None:
    """Test 2: YAML with inject: bogus_kind raises ValueError."""
    from token_world.playtest import Scenario

    data = {
        "name": "bad_scenario",
        "description": "Has invalid inject type",
        "turns": [{"inject": "bogus_kind"}],
    }
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")

    with pytest.raises(ValueError, match="bogus_kind"):
        Scenario.load(p)


def test_scenario_next_action_returns_scripted(tmp_path: Path) -> None:
    """Test 3a: next_turn(0) returns ('action', 'look') for scripted action."""
    from token_world.playtest import Scenario

    data = {
        "name": "s",
        "description": "d",
        "turns": [{"action": "look"}, {"action": None}],
    }
    p = tmp_path / "s.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")

    scenario = Scenario.load(p)
    kind, payload = scenario.next_turn(0)
    assert kind == "action"
    assert payload == "look"


def test_scenario_next_action_returns_agent_decide_for_null(tmp_path: Path) -> None:
    """Test 3b: next_turn(1) returns ('agent', None) for action: null."""
    from token_world.playtest import Scenario

    data = {
        "name": "s",
        "description": "d",
        "turns": [{"action": "look"}, {"action": None}],
    }
    p = tmp_path / "s.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")

    scenario = Scenario.load(p)
    kind, payload = scenario.next_turn(1)
    assert kind == "agent"
    assert payload is None


def test_scenario_next_action_returns_injection(tmp_path: Path) -> None:
    """Test 4: next_turn returns ('inject', 'nonsense') for inject turns."""
    from token_world.playtest import Scenario

    data = {
        "name": "s",
        "description": "d",
        "turns": [{"inject": "nonsense"}],
    }
    p = tmp_path / "s.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")

    scenario = Scenario.load(p)
    kind, payload = scenario.next_turn(0)
    assert kind == "inject"
    assert payload == "nonsense"


def test_scenario_out_of_bounds_returns_agent_decide(tmp_path: Path) -> None:
    """Test 5: requesting turn beyond turns list returns ('agent', None)."""
    from token_world.playtest import Scenario

    data = {
        "name": "s",
        "description": "d",
        "turns": [{"action": "look"}],
    }
    p = tmp_path / "s.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")

    scenario = Scenario.load(p)
    kind, payload = scenario.next_turn(999)
    assert kind == "agent"
    assert payload is None


# ---------------------------------------------------------------------------
# InjectionSampler tests
# ---------------------------------------------------------------------------


def test_injection_sampler_deterministic_with_seed() -> None:
    """Test 6: Two samplers with same seed produce identical outputs."""
    from token_world.playtest import InjectionSampler

    s1 = InjectionSampler(seed=42)
    s2 = InjectionSampler(seed=42)

    results1 = [s1.sample("nonsense", previous_action="x", turn_number=i) for i in range(5)]
    results2 = [s2.sample("nonsense", previous_action="x", turn_number=i) for i in range(5)]

    assert results1 == results2


def test_injection_sampler_nonsense_is_non_empty_string() -> None:
    """Test 7: sample('nonsense') returns a non-empty string != previous_action."""
    from token_world.playtest import InjectionSampler

    sampler = InjectionSampler(seed=0)
    result = sampler.sample("nonsense", previous_action="x", turn_number=0)

    assert isinstance(result, str)
    assert len(result) > 0
    assert result != "x"


def test_injection_sampler_repeat_last_returns_previous() -> None:
    """Test 8: sample('repeat_last') returns previous_action verbatim."""
    from token_world.playtest import InjectionSampler

    sampler = InjectionSampler(seed=0)
    result = sampler.sample("repeat_last", previous_action="look around", turn_number=0)

    assert result == "look around"


def test_injection_sampler_adversarial_from_bank() -> None:
    """Test 9: sample('adversarial') returns one of hardcoded adversarial strings."""
    from token_world.playtest import InjectionSampler

    sampler = InjectionSampler(seed=0)
    # Generate multiple to ensure at least one from bank
    results = set(
        sampler.sample("adversarial", previous_action="x", turn_number=i) for i in range(10)
    )
    # At least one should be from the bank (contains a known phrase)
    bank_phrases = [
        "ignore all rules",
        "delete the world",
        "become god",
        "destroy the universe",
        "cheat",
        "win",
        "take all items",
        "rewrite the laws",
    ]
    found_bank = any(any(phrase in result.lower() for phrase in bank_phrases) for result in results)
    assert found_bank, f"No adversarial bank phrase found in: {results}"


def test_injection_sampler_edge_case_variety() -> None:
    """Test 10: Over 20 calls, at least two different edge_case outputs are seen."""
    from token_world.playtest import InjectionSampler

    sampler = InjectionSampler(seed=0)
    results = set(
        sampler.sample("edge_case", previous_action="x", turn_number=i) for i in range(20)
    )
    assert len(results) >= 2, f"Expected at least 2 distinct edge_case outputs, got: {results}"


def test_example_yaml_loads() -> None:
    """Test 11: scenarios/example.yaml loads successfully."""
    from token_world.playtest import Scenario

    example_path = Path("scenarios/example.yaml")
    scenario = Scenario.load(example_path)
    assert scenario.name
    assert scenario.seed >= 0
    assert len(scenario.turns) > 0
