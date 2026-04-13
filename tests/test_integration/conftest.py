"""Shared fixtures for the Phase-4 use-case-driven integration harness (TEST-02).

The ``diagnostics_sink`` fixture exercises the D-23 ``DiagnosticsSink`` API as
the Phase-4 consumer side of AUTO-02. Phase 5 will wire the classifier /
observer LLM calls into the same sink; every harness run writing
``tick_<N>/summary.json`` here proves the API is consumer-ready before the
LLM plumbing arrives.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from token_world.graph import KnowledgeGraph
from token_world.mechanic.diagnostics import DiagnosticsSink

# Absolute paths anchored at the repo root (two parents up from this file:
# tests/test_integration/conftest.py -> repo root).
REPO_ROOT = Path(__file__).resolve().parents[2]
USE_CASES_DIR = REPO_ROOT / ".planning" / "use-cases"
SEEDS_DIR = REPO_ROOT / "src" / "token_world" / "mechanic" / "seeds"
CATEGORIES = ("spatial", "social", "resource", "environmental", "edge-case")


@pytest.fixture
def harness_kg() -> KnowledgeGraph:
    """Fresh in-memory :class:`KnowledgeGraph` for each use-case run."""
    return KnowledgeGraph()


@pytest.fixture
def diagnostics_sink(tmp_path: Path) -> DiagnosticsSink:
    """Per-test :class:`DiagnosticsSink` rooted at ``tmp_path`` (D-23).

    Phase 4's consumer-side exercise of AUTO-02: every harness invocation
    opens a tick context and writes a summary.json with ``uc_id``. When
    Phase 5 plugs the classifier/observer LLM calls into the same sink,
    the wiring pattern demonstrated here is the template.
    """
    return DiagnosticsSink(tmp_path)
