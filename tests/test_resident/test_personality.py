"""Tests for PersonalityBundle and PersonalityGenerator (Task 1 TDD)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.test_resident.conftest import MockAnthropicClient
from token_world.resident.personality import PersonalityBundle, PersonalityGenerator

_VALID_JSON = (
    '{"name":"Elara","archetype":"curious wanderer",'
    '"traits":["inquisitive","brave","kind"],'
    '"backstory":"She grew up exploring the misty caves. She seeks truth.",'
    '"speech_style":"speaks in clipped sentences"}'
)


def test_personality_bundle_validates_shape() -> None:
    """PersonalityBundle accepts valid input; rejects <3 or >5 traits."""
    bundle = PersonalityBundle(
        name="X",
        archetype="Y",
        traits=["a", "b", "c"],
        backstory="bs",
        speech_style="ss",
    )
    assert bundle.name == "X"
    assert len(bundle.traits) == 3

    with pytest.raises(ValidationError):
        PersonalityBundle(
            name="X",
            archetype="Y",
            traits=[],
            backstory="bs",
            speech_style="ss",
        )

    with pytest.raises(ValidationError):
        PersonalityBundle(
            name="X",
            archetype="Y",
            traits=["a", "b", "c", "d", "e", "f"],
            backstory="bs",
            speech_style="ss",
        )


def test_personality_bundle_roundtrips_json() -> None:
    """model_dump_json + model_validate_json yields an equal bundle."""
    original = PersonalityBundle(
        name="Elara",
        archetype="wanderer",
        traits=["brave", "curious", "kind"],
        backstory="She roams the world.",
        speech_style="verbose",
    )
    serialized = original.model_dump_json()
    restored = PersonalityBundle.model_validate_json(serialized)
    assert restored == original


def test_generator_calls_sonnet_and_parses_json() -> None:
    """PersonalityGenerator.generate makes one Sonnet call and parses valid JSON."""
    client = MockAnthropicClient([_VALID_JSON])
    generator = PersonalityGenerator()
    bundle = generator.generate("A misty cavern world", client=client)

    assert bundle.name == "Elara"
    assert bundle.archetype == "curious wanderer"
    assert "inquisitive" in bundle.traits
    assert len(bundle.traits) == 3

    assert len(client.messages.calls) == 1
    assert client.messages.calls[0]["model"] == "claude-sonnet-4-5"


def test_generator_retries_once_on_malformed_json() -> None:
    """Generator retries once on malformed JSON; succeeds on second call."""
    client = MockAnthropicClient(["not json at all", _VALID_JSON])
    generator = PersonalityGenerator()
    bundle = generator.generate("misty world", client=client)
    assert bundle.name == "Elara"
    assert len(client.messages.calls) == 2

    # Both calls fail → ValueError
    client_bad = MockAnthropicClient(["bad1", "bad2"])
    with pytest.raises(ValueError, match="personality generation failed"):
        generator.generate("misty world", client=client_bad)


def test_generator_extracts_json_from_wrapped_prose() -> None:
    """Generator handles JSON wrapped in surrounding prose text."""
    wrapped = f"Here's the personality:\n{_VALID_JSON}\nDone!"
    client = MockAnthropicClient([wrapped])
    generator = PersonalityGenerator()
    bundle = generator.generate("a world", client=client)
    assert bundle.name == "Elara"
