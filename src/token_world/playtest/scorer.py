"""TurnScorer: five deterministic rubric metrics per D-12.

Metrics (each 0.0-1.0, averaged into composite):
    1. mechanic_match_rate   -- 1.0 if ok, 0.0 if yielded, 0.5 if refused
    2. observation_groundedness -- 1.0 if obs contains a projected_state node id, else 0.5
    3. mutation_count        -- 1.0 if mutations>0, 0.5 if trace but empty, 0.0 if refused
    4. refusal_rate          -- rolling non-refusal ratio (higher = fewer refusals)
    5. action_novelty        -- 1 - max_cosine(current, last 3 actions); D-30

Decision D-30: cosine on word-bag Counter, stdlib only (no numpy/scipy).
"""

from __future__ import annotations

from collections import Counter
from math import sqrt

from pydantic import BaseModel

from token_world.mechanic.trace import collect_mutations


class TurnScore(BaseModel):
    """Scores for a single playtest turn. All metrics in [0.0, 1.0].

    Attributes:
        mechanic_match_rate: 1.0=ok, 0.0=yielded, 0.5=refused.
        observation_groundedness: 1.0 if obs mentions a projected node id, else 0.5.
        mutation_count: 1.0=has mutations, 0.5=trace empty, 0.0=refused (no trace).
        refusal_rate: rolling fraction of non-refusal turns (1.0 = no refusals yet).
        action_novelty: 1 - max cosine similarity against last 3 actions.
        composite: mean of the five metrics.
    """

    mechanic_match_rate: float
    observation_groundedness: float
    mutation_count: float
    refusal_rate: float
    action_novelty: float
    composite: float


class TurnScorer:
    """Stateless scorer that computes D-12 metrics for a single turn.

    All methods are pure (no side effects); call score() after each turn.
    """

    def score(
        self,
        *,
        result: object,
        action_text: str,
        action_history: list[str],
        previous_non_refusal_count: int,
        total_turns_so_far: int,
    ) -> TurnScore:
        """Compute the five D-12 metrics for one turn.

        Args:
            result: TickResult from SimulationEngine.run_tick().
            action_text: The action text sent to the engine this turn.
            action_history: List of previous action texts (up to last 3 used).
            previous_non_refusal_count: Count of non-refusal turns BEFORE this turn.
            total_turns_so_far: Zero-based index of the current turn.

        Returns:
            A TurnScore with all five metrics and the composite mean.
        """
        kind = result.kind  # type: ignore[attr-defined]
        refusal_reason = getattr(result, "refusal_reason", None)

        mmr = self._mechanic_match_rate(kind, refusal_reason)
        grnd = self._observation_groundedness(result, kind)
        mut = self._mutation_count(result, kind, refusal_reason)
        ref = self._refusal_rate(kind, previous_non_refusal_count, total_turns_so_far)
        nov = self._action_novelty(action_text, action_history[-3:] if action_history else [])

        composite = (mmr + grnd + mut + ref + nov) / 5.0
        return TurnScore(
            mechanic_match_rate=mmr,
            observation_groundedness=grnd,
            mutation_count=mut,
            refusal_rate=ref,
            action_novelty=nov,
            composite=composite,
        )

    # -------------------------------------------------------------------------
    # Metric implementations
    # -------------------------------------------------------------------------

    @staticmethod
    def _mechanic_match_rate(kind: str, refusal_reason: str | None = None) -> float:
        """D-12 metric 1: 1.0=ok, 0.0=yielded, 0.5=refused.

        §E6: ``mechanic_check_failed`` refusals score like ``ok`` because a
        mechanic *was* matched and dispatched — only the runtime precondition
        check said "no". Scoring them at 0.5 would double-penalise what is now
        an honest refusal (previously mis-recorded as a 0-mutation execute).
        """
        if kind == "ok":
            return 1.0
        elif kind == "yielded":
            return 0.0
        elif kind == "refused" and refusal_reason == "mechanic_check_failed":
            return 1.0
        else:  # refused
            return 0.5

    @staticmethod
    def _observation_groundedness(result: object, kind: str) -> float:
        """D-12 metric 2: substring check of projected_state node ids in observation.

        Uses result.projected_state (Wave-0 06-00 field) and result.observation.
        Returns 1.0 if >= 1 node id from projected_state appears as substring in
        the observation text; else 0.5.  Yield/refuse paths return 0.5 (no observer ran).
        """
        projected_state = getattr(result, "projected_state", None)
        observation = getattr(result, "observation", None)

        if not projected_state or observation is None:
            return 0.5

        obs_lower = observation.lower()
        for node_id in projected_state:
            if node_id.lower() in obs_lower:
                return 1.0

        return 0.5

    @staticmethod
    def _mutation_count(result: object, kind: str, refusal_reason: str | None = None) -> float:
        """D-12 metric 3: 1.0 if mutations, 0.5 if trace but empty, 0.0 if refused (no trace).

        §E6: ``mechanic_check_failed`` refusals score 0.5 (not 0.0) because a
        mechanic was dispatched and its check() ran — the tick was structurally
        "an executed mechanic that chose not to mutate", matching the existing
        0.5 rung for "trace exists but empty". Other refusal reasons (classifier
        refuse, conservation_violation, engine_error) still score 0.0 because
        no mechanic was dispatched or its work was rolled back.
        """
        if kind == "refused" and refusal_reason == "mechanic_check_failed":
            return 0.5
        if kind == "refused":
            return 0.0

        trace = getattr(result, "trace", None)
        if trace is None:
            # yielded path also has no trace
            return 0.5

        # Walk the trace tree to count all mutations — delegates to the shared
        # mechanic.trace walker (IN-02 dedup, 2026-04-14).
        total = len(collect_mutations(trace))

        return 1.0 if total > 0 else 0.5

    @staticmethod
    def _refusal_rate(kind: str, previous_non_refusal_count: int, total_turns_so_far: int) -> float:
        """D-12 metric 4: rolling non-refusal fraction.

        Formula: (previous_non_refusal_count + (0 if refused else 1)) / (total_turns_so_far + 1)
        1.0 means no refusals in any turn; 0.0 means every turn was refused.
        """
        increment = 0 if kind == "refused" else 1
        denominator = total_turns_so_far + 1
        return (previous_non_refusal_count + increment) / max(1, denominator)

    @staticmethod
    def _word_bag(text: str) -> Counter:
        """Lowercase word-bag Counter for cosine similarity (D-30)."""
        words = [w for w in text.lower().split() if w.isalnum()]
        return Counter(words)

    @classmethod
    def _cosine(cls, a: Counter, b: Counter) -> float:
        """Cosine similarity between two word-bag Counters (D-30, stdlib only).

        Returns 0.0 if either bag is empty (undefined similarity -> treat as different).
        """
        if not a or not b:
            return 0.0
        # Dot product
        dot = sum(a[w] * b.get(w, 0) for w in a)
        norm_a = sqrt(sum(v * v for v in a.values()))
        norm_b = sqrt(sum(v * v for v in b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @classmethod
    def _action_novelty(cls, action_text: str, recent_history: list[str]) -> float:
        """D-12 metric 5: 1 - max cosine similarity against last 3 actions.

        Returns 1.0 for the first turn (empty history = fully novel).
        Returns 0.0 for an identical repeat.
        """
        if not recent_history:
            return 1.0

        current_bag = cls._word_bag(action_text)
        max_sim = max(cls._cosine(current_bag, cls._word_bag(prev)) for prev in recent_history)
        return 1.0 - max_sim
