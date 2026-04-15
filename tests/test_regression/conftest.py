"""Regression suite fixtures: fake LLM clients + graph-builder exec.

DVAL-03. Provides isolated, cost-free test harness for exercising the real
engine pipeline (classifier → matcher → mechanics → conservation → observer)
without calling Anthropic APIs.
"""

from __future__ import annotations

import shutil
import unittest.mock as mock
from pathlib import Path
from typing import Any

import pytest

from token_world.engine.engine import SimulationEngine
from token_world.engine.models import ClassifiedAction, VerdictOk
from token_world.graph import KnowledgeGraph

# ---------------------------------------------------------------------------
# Restricted exec namespace for graph_builder code from UC manifests
# ---------------------------------------------------------------------------

_EXEC_NS_BASE: dict[str, Any] = {
    "__builtins__": {
        "range": range,
        "print": print,
        "len": len,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "True": True,
        "False": False,
        "None": None,
    }
}

# Seed mechanics are copied into the test universe to allow real mechanic
# matching. Without them, all "pass" UCs would yield (no mechanic found).
_SEEDS_SRC = Path(__file__).resolve().parents[2] / "src" / "token_world" / "mechanic" / "seeds"


def exec_graph_builder(code: str, kg: KnowledgeGraph) -> None:
    """Execute a UC manifest's setup.graph_builder code against kg.

    Namespace is restricted to prevent __import__ and other escapes.
    Mirrors tests/test_integration/ pattern (06-RESEARCH Pitfall 2 mitigation).

    Raises:
        NameError: If the code references names not in the restricted namespace.
        SyntaxError: If the code has syntax errors.
    """
    ns = {**_EXEC_NS_BASE, "kg": kg}
    exec(compile(code, "<uc_setup>", "exec"), ns, ns)  # noqa: S102


# ---------------------------------------------------------------------------
# Fake LLM clients
# ---------------------------------------------------------------------------


class FakeClassifier:
    """Deterministic classifier that returns the UC manifest's pre-classified action.

    Skips the Haiku LLM call entirely, returning VerdictOk with the manifest's
    classified dict. This makes regression tests deterministic and free.
    """

    last_input_tokens: int = 0
    last_output_tokens: int = 0

    def __init__(self, classified_dict: dict[str, Any]) -> None:
        self._classified_dict = classified_dict

    def classify(
        self,
        action_text: str,
        actor: str,
        *,
        available_verbs: list[str],
        known_node_ids: list[str],
        min_confidence: float = 0.6,
        tick_diag_ctx: Any = None,
    ) -> VerdictOk:
        # actor is always injected; classified_dict may already have it
        merged = {"actor": actor, **self._classified_dict}
        return VerdictOk(
            actions=[ClassifiedAction(**merged)],
            confidence=0.99,
        )


class FakeObserver:
    """Deterministic observer that returns a fixed success narrative.

    Per 06-RESEARCH §Open Question 2: the regression suite tests mechanic
    matching + graph assertions, not observer prose. Calling real Sonnet 35×
    per CI run would cost ~$0.05 and introduce flakiness.
    """

    last_input_tokens: int = 0
    last_output_tokens: int = 0

    def synthesize(
        self,
        *,
        projection: dict[str, Any],
        trace: Any,
        refusal_narrative: str | None = None,
        actor_id: str,
        action_text: str = "",
        tick_diag_ctx: Any = None,
    ) -> str:
        if refusal_narrative is not None:
            return refusal_narrative
        return "Action succeeded."


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_anthropic_client() -> mock.MagicMock:
    """Bare MagicMock for the Anthropic client.

    FakeClassifier/FakeObserver bypass the client entirely; this mock satisfies
    SimulationEngine's type requirement.
    """
    return mock.MagicMock()


@pytest.fixture
def build_engine(tmp_path: Path, fake_anthropic_client: mock.MagicMock):
    """Return a callable (kg, classified_dict) -> SimulationEngine.

    The returned engine has FakeClassifier and FakeObserver wired in place of
    real Anthropic clients. Seed mechanics are copied into the universe dir so
    real mechanic matching can run.

    Usage:
        engine = build_engine(kg, {"verb": "look", "target": "room"})
        result = engine.run_tick("look around", actor="alice")
    """

    def _build(kg: KnowledgeGraph, classified_dict: dict[str, Any]) -> SimulationEngine:
        universe = tmp_path / "test_universe"
        mechanics_dir = universe / "mechanics"
        mechanics_dir.mkdir(parents=True, exist_ok=True)

        # Copy seed mechanics into the test universe so real mechanic matching works.
        # Without this, all "pass" UCs would yield (no mechanic found).
        if _SEEDS_SRC.exists():
            for py_file in _SEEDS_SRC.rglob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                # Preserve subdirectory structure for seed packages (e.g. movement/)
                relative = py_file.relative_to(_SEEDS_SRC)
                dest = mechanics_dir / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(py_file, dest)

        engine = SimulationEngine(
            universe,
            graph=kg,
            anthropic_client=fake_anthropic_client,
        )
        # Swap in fakes after construction (attribute-level patch; acceptable in test infra)
        engine._classifier = FakeClassifier(classified_dict)  # type: ignore[assignment]
        engine._observer = FakeObserver()  # type: ignore[assignment]
        return engine

    return _build
