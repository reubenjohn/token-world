"""Unit tests for the Haiku-backed Classifier (D-04, D-05, D-06).

Uses MockAnthropicClient to inject canned responses without real API calls.
"""

from __future__ import annotations

import json

from token_world.engine.classifier import Classifier
from token_world.engine.models import (
    VerdictLowConfidence,
    VerdictNoSuchTarget,
    VerdictNoViableAction,
    VerdictOk,
)

# ---------------------------------------------------------------------------
# Mock client (Task 5 inline, Task 6 will centralise to conftest)
# ---------------------------------------------------------------------------


class _Block:
    def __init__(self, text: str) -> None:
        self.text = text


class _Response:
    def __init__(self, text: str) -> None:
        self.content = [_Block(text)]


class _MessagesProxy:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses:
            raise RuntimeError("MockAnthropicClient ran out of responses")
        return _Response(self._responses.pop(0))


class MockAnthropicClient:
    def __init__(self, responses: list[str]) -> None:
        self.messages = _MessagesProxy(responses)


def _clf(responses: list[str], **kwargs) -> tuple[Classifier, MockAnthropicClient]:
    client = MockAnthropicClient(responses)
    clf = Classifier(client=client, **kwargs)
    return clf, client


_OK_RESPONSE = json.dumps(
    {
        "kind": "ok",
        "classified": {"verb": "pickup", "actor": "alice", "target": "rock_1", "params": {}},
        "confidence": 0.95,
    }
)

_NVA_RESPONSE = json.dumps({"kind": "no_viable_action", "reason": "gibberish"})
_NST_RESPONSE = json.dumps({"kind": "no_such_target", "target_text": "the dragon"})
_LOW_CONF_RESPONSE = json.dumps(
    {
        "kind": "low_confidence",
        "reason": "ambiguous",
        "confidence": 0.4,
    }
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestClassifierBasicVerdicts:
    """Classifier returns the correct verdict type for each shape."""

    def test_ok_verdict_returned(self) -> None:
        """Well-formed ok response -> VerdictOk."""
        clf, _ = _clf([_OK_RESPONSE])
        result = clf.classify(
            "pick up the rock",
            "alice",
            available_verbs=["pickup"],
            known_node_ids=["alice", "rock_1"],
        )
        assert isinstance(result, VerdictOk)
        assert result.classified.verb == "pickup"

    def test_no_viable_action_returned(self) -> None:
        """Well-formed no_viable_action -> VerdictNoViableAction."""
        clf, _ = _clf([_NVA_RESPONSE])
        result = clf.classify(
            "blahblah", "alice", available_verbs=["pickup"], known_node_ids=["alice"]
        )
        assert isinstance(result, VerdictNoViableAction)

    def test_no_such_target_returned(self) -> None:
        """Well-formed no_such_target -> VerdictNoSuchTarget."""
        clf, _ = _clf([_NST_RESPONSE])
        result = clf.classify(
            "attack the dragon", "alice", available_verbs=["attack"], known_node_ids=["alice"]
        )
        assert isinstance(result, VerdictNoSuchTarget)

    def test_low_confidence_returned(self) -> None:
        """Well-formed low_confidence -> VerdictLowConfidence."""
        clf, _ = _clf([_LOW_CONF_RESPONSE])
        result = clf.classify(
            "maybe do something", "alice", available_verbs=["pickup"], known_node_ids=["alice"]
        )
        assert isinstance(result, VerdictLowConfidence)


class TestClassifierRetry:
    """Classifier retries once on malformed JSON."""

    def test_malformed_then_ok(self) -> None:
        """First response malformed, second valid -> returns parsed verdict."""
        clf, _ = _clf(["NOT JSON AT ALL", _OK_RESPONSE])
        result = clf.classify(
            "pick up rock", "alice", available_verbs=["pickup"], known_node_ids=["alice", "rock_1"]
        )
        assert isinstance(result, VerdictOk)

    def test_both_malformed_returns_no_viable_action(self) -> None:
        """Both attempts malformed -> VerdictNoViableAction with 'malformed' in reason."""
        clf, _ = _clf(["bad json", "also bad"])
        result = clf.classify(
            "pick up rock", "alice", available_verbs=["pickup"], known_node_ids=["alice"]
        )
        assert isinstance(result, VerdictNoViableAction)
        assert "malformed" in result.reason.lower()

    def test_empty_response_retries_and_returns_no_viable_action(self) -> None:
        """Empty response on both attempts -> VerdictNoViableAction."""
        clf, _ = _clf(["", ""])
        result = clf.classify(
            "do something", "alice", available_verbs=["pickup"], known_node_ids=["alice"]
        )
        assert isinstance(result, VerdictNoViableAction)


class TestClassifierPostProcessing:
    """Post-processing: confidence threshold + known-node target check."""

    def test_ok_below_threshold_becomes_low_confidence(self) -> None:
        """Ok with confidence 0.5, threshold 0.6 -> VerdictLowConfidence."""
        low_ok = json.dumps(
            {
                "kind": "ok",
                "classified": {
                    "verb": "pickup",
                    "actor": "alice",
                    "target": "rock_1",
                    "params": {},
                },
                "confidence": 0.5,
            }
        )
        clf, _ = _clf([low_ok])
        result = clf.classify(
            "pick up rock",
            "alice",
            available_verbs=["pickup"],
            known_node_ids=["alice", "rock_1"],
            min_confidence=0.6,
        )
        assert isinstance(result, VerdictLowConfidence)

    def test_ok_target_not_in_known_nodes_becomes_no_such_target(self) -> None:
        """Ok verdict with target not in known_node_ids -> VerdictNoSuchTarget."""
        clf, _ = _clf([_OK_RESPONSE])
        # rock_1 not in known_node_ids
        result = clf.classify(
            "pick up rock",
            "alice",
            available_verbs=["pickup"],
            known_node_ids=["alice"],
            min_confidence=0.0,
        )
        assert isinstance(result, VerdictNoSuchTarget)
        assert result.target_text == "rock_1"

    def test_extra_fields_in_response_ignored(self) -> None:
        """Extra fields in Haiku response are silently dropped."""
        response_with_extras = json.dumps(
            {
                "kind": "ok",
                "classified": {
                    "verb": "pickup",
                    "actor": "alice",
                    "target": "rock_1",
                    "params": {},
                    "extra_llm_field": "ignored",
                },
                "confidence": 0.9,
                "some_reasoning": "I think this is correct",
            }
        )
        clf, _ = _clf([response_with_extras])
        result = clf.classify(
            "pick up rock", "alice", available_verbs=["pickup"], known_node_ids=["alice", "rock_1"]
        )
        assert isinstance(result, VerdictOk)


class TestClassifierIndirectObjectValidation:
    """WR-02: indirect_object must be validated against known_node_ids."""

    def test_hallucinated_indirect_object_becomes_no_such_target(self) -> None:
        """Ok verdict with indirect_object not in known_node_ids -> VerdictNoSuchTarget.

        WR-02: Haiku may hallucinate a non-existent indirect_object node ID.
        The classifier must catch this and return VerdictNoSuchTarget, just as
        it does for a hallucinated target.
        """
        response_with_indirect = json.dumps(
            {
                "kind": "ok",
                "classified": {
                    "verb": "give",
                    "actor": "alice",
                    "target": "gold_coin",
                    "indirect_object": "phantom_bob",  # not in known_node_ids
                    "params": {},
                },
                "confidence": 0.95,
            }
        )
        clf, _ = _clf([response_with_indirect])
        result = clf.classify(
            "give gold coin to bob",
            "alice",
            available_verbs=["give"],
            known_node_ids=["alice", "gold_coin"],  # phantom_bob is absent
            min_confidence=0.0,
        )
        assert isinstance(result, VerdictNoSuchTarget)
        assert result.target_text == "phantom_bob"

    def test_valid_indirect_object_does_not_become_no_such_target(self) -> None:
        """Ok verdict with indirect_object IN known_node_ids stays VerdictOk."""
        response_with_indirect = json.dumps(
            {
                "kind": "ok",
                "classified": {
                    "verb": "give",
                    "actor": "alice",
                    "target": "gold_coin",
                    "indirect_object": "bob",
                    "params": {},
                },
                "confidence": 0.95,
            }
        )
        clf, _ = _clf([response_with_indirect])
        result = clf.classify(
            "give gold coin to bob",
            "alice",
            available_verbs=["give"],
            known_node_ids=["alice", "gold_coin", "bob"],
            min_confidence=0.0,
        )
        assert isinstance(result, VerdictOk)
        assert result.classified.indirect_object == "bob"

    def test_null_indirect_object_does_not_trigger_validation(self) -> None:
        """Ok verdict with indirect_object=None does not trigger no_such_target."""
        clf, _ = _clf([_OK_RESPONSE])
        result = clf.classify(
            "pick up the rock",
            "alice",
            available_verbs=["pickup"],
            known_node_ids=["alice", "rock_1"],
            min_confidence=0.0,
        )
        assert isinstance(result, VerdictOk)


class TestClassifierDiagnostics:
    """Diagnostics sink receives prompt/response/parsed calls."""

    def test_tick_diag_ctx_receives_write_calls(self) -> None:
        """write_prompt, write_response, write_parsed are called on tick_diag_ctx."""
        calls: list[tuple] = []

        class MockDiagCtx:
            def write_prompt(self, stage, text):
                calls.append(("prompt", stage))

            def write_response(self, stage, text, suffix=""):
                calls.append(("response", stage, suffix))

            def write_parsed(self, stage, data):
                calls.append(("parsed", stage))

        clf, _ = _clf([_OK_RESPONSE])
        clf.classify(
            "pick up rock",
            "alice",
            available_verbs=["pickup"],
            known_node_ids=["alice", "rock_1"],
            tick_diag_ctx=MockDiagCtx(),
        )
        stages = [c[1] for c in calls]
        assert "classification" in stages
        assert any(c[0] == "prompt" for c in calls)
        assert any(c[0] == "response" for c in calls)
        assert any(c[0] == "parsed" for c in calls)
