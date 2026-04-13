"""Tests for AdversarialBank class — deterministic categorized corpus (Task 1, AUTO-05)."""

from __future__ import annotations

import random

# ---------------------------------------------------------------------------
# Test 1: minimum entries per category
# ---------------------------------------------------------------------------


def test_adversarial_bank_has_minimum_entries_per_category() -> None:
    """Test 1 (RED): Each category has >= 8 entries; total >= 50."""
    from token_world.playtest.adversarial import AdversarialBank

    bank = AdversarialBank()
    counts = bank.count_by_category()

    expected_categories = {
        "nonsense",
        "rule_violation",
        "boundary_probe",
        "role_break",
        "recursive_meta",
    }
    assert set(counts.keys()) >= expected_categories, (
        f"Missing categories: {expected_categories - set(counts.keys())}"
    )

    for cat in expected_categories:
        assert counts[cat] >= 8, f"Category {cat!r} has only {counts[cat]} entries (expected >= 8)"

    total = sum(counts.values())
    assert total >= 50, f"Total entries {total} < 50"


# ---------------------------------------------------------------------------
# Test 2: sample returns entry text
# ---------------------------------------------------------------------------


def test_sample_returns_entry_text() -> None:
    """Test 2 (RED): bank.sample(rng) returns a string from the corpus."""
    from token_world.playtest.adversarial import AdversarialBank

    bank = AdversarialBank()
    rng = random.Random(42)

    result = bank.sample(rng)
    assert isinstance(result, str)

    all_texts = {e.text for e in bank.list_all()}
    assert result in all_texts, f"Sampled {result!r} not found in corpus"


# ---------------------------------------------------------------------------
# Test 3: deterministic with seed
# ---------------------------------------------------------------------------


def test_sample_is_deterministic_with_seed() -> None:
    """Test 3 (RED): Two identically-seeded RNGs produce the same sample sequence."""
    from token_world.playtest.adversarial import AdversarialBank

    bank1 = AdversarialBank()
    bank2 = AdversarialBank()
    rng1 = random.Random(99)
    rng2 = random.Random(99)

    seq1 = [bank1.sample(rng1) for _ in range(20)]
    seq2 = [bank2.sample(rng2) for _ in range(20)]

    assert seq1 == seq2, "Same seed must produce identical sequences"


# ---------------------------------------------------------------------------
# Test 4: sample by category filters
# ---------------------------------------------------------------------------


def test_sample_by_category_filters() -> None:
    """Test 4 (RED): bank.sample(rng, category='role_break') only returns role_break entries."""
    from token_world.playtest.adversarial import AdversarialBank

    bank = AdversarialBank()
    role_break_texts = {e.text for e in bank.list_all() if e.category == "role_break"}
    rng = random.Random(7)

    for _ in range(30):
        result = bank.sample(rng, category="role_break")
        assert result in role_break_texts, f"{result!r} is not a role_break entry"


# ---------------------------------------------------------------------------
# Test 5: sample by difficulty filters
# ---------------------------------------------------------------------------


def test_sample_by_difficulty_filters() -> None:
    """Test 5 (RED): bank.sample(rng, max_difficulty=1) only returns difficulty-1 entries."""
    from token_world.playtest.adversarial import AdversarialBank

    bank = AdversarialBank()
    diff1_texts = {e.text for e in bank.list_all() if e.difficulty == 1}
    rng = random.Random(13)

    for _ in range(30):
        result = bank.sample(rng, max_difficulty=1)
        assert result in diff1_texts, f"{result!r} is not a difficulty-1 entry"


# ---------------------------------------------------------------------------
# Test 6: no duplicate text in corpus
# ---------------------------------------------------------------------------


def test_list_all_returns_unique_entries() -> None:
    """Test 6 (RED): No duplicate text strings appear in the corpus."""
    from token_world.playtest.adversarial import AdversarialBank

    bank = AdversarialBank()
    all_entries = bank.list_all()
    texts = [e.text for e in all_entries]
    unique_texts = set(texts)

    assert len(texts) == len(unique_texts), (
        f"Duplicates found: {[t for t in texts if texts.count(t) > 1]}"
    )


# ---------------------------------------------------------------------------
# Test 7: no shell injection patterns
# ---------------------------------------------------------------------------


def test_bank_entries_have_no_shell_injection_patterns() -> None:
    """Test 7 (RED): No entry contains shell-injection patterns (narrative-level only)."""
    from token_world.playtest.adversarial import AdversarialBank

    FORBIDDEN_PATTERNS = ["rm -rf", "`", "$(", "&& rm", "|| rm"]

    bank = AdversarialBank()
    violations = []
    for entry in bank.list_all():
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in entry.text:
                violations.append((entry.text, pattern))

    assert not violations, f"Shell injection patterns found: {violations}"


# ---------------------------------------------------------------------------
# Test: InjectionSampler adversarial type uses AdversarialBank
# ---------------------------------------------------------------------------


def test_injection_sampler_adversarial_uses_bank() -> None:
    """Test: InjectionSampler adversarial inject returns a string from AdversarialBank."""
    from token_world.playtest import InjectionSampler
    from token_world.playtest.adversarial import AdversarialBank

    bank = AdversarialBank()
    all_texts = {e.text for e in bank.list_all()}

    sampler = InjectionSampler(seed=42)
    # Sample many times to cover different draws
    for i in range(20):
        result = sampler.sample("adversarial", previous_action="x", turn_number=i)
        assert isinstance(result, str)
        assert result in all_texts, (
            f"adversarial inject returned {result!r} which is not in AdversarialBank"
        )
