"""Pydantic models for Token World data structures."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator


class UniverseMetadata(BaseModel):
    """Metadata for a universe instance, stored in universe.db."""

    name: str = Field(min_length=1, description="Display name of the universe")
    slug: str = Field(min_length=1, description="Slugified folder name")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    schema_version: int = Field(default=1)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Universe name cannot be blank")
        return v.strip()
