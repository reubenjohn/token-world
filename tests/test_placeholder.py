"""Placeholder test to ensure pytest collects at least one test."""

from token_world import __version__


def test_version() -> None:
    """Verify the package version is set."""
    assert __version__ == "0.1.0"
