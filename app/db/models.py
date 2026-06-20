"""
SQLAlchemy ORM models.

These models define the persistent schema.  Alembic migrations (in alembic/versions/)
are generated from these definitions — never edit the database schema directly.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


class Estimate(Base):
    """
    Persisted damage-estimate record.

    One row is created per ``POST /api/v1/estimates`` request.  The status
    field is updated asynchronously as AI offices process the job.
    """

    __tablename__ = "estimates"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="UUID v4 — matches the estimate_id returned to clients",
    )

    # ── Client / vehicle ──────────────────────────────────────────────────────
    client_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Unique identifier for the client repair shop",
    )
    vehicle_vin: Mapped[str] = mapped_column(
        String(17),
        nullable=False,
        comment="17-character Vehicle Identification Number",
    )
    vehicle_year: Mapped[int] = mapped_column(Integer, nullable=False)
    vehicle_make: Mapped[str] = mapped_column(String(64), nullable=False)
    vehicle_model: Mapped[str] = mapped_column(String(64), nullable=False)

    # ── Damage details ────────────────────────────────────────────────────────
    damage_description: Mapped[str] = mapped_column(Text, nullable=False)
    photo_urls: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        comment="JSON-encoded list of photo URLs",
    )
    office_ids: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[1]",
        comment="JSON-encoded list of AI office IDs to involve",
    )

    # ── Processing state ──────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        comment="pending | processing | completed | failed",
    )
    estimated_total_usd: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Final estimate in USD, populated when status=completed",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_estimates_client_id", "client_id"),
        Index("ix_estimates_vehicle_vin", "vehicle_vin"),
        Index("ix_estimates_status", "status"),
        Index("ix_estimates_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Estimate id={self.id!r} client={self.client_id!r} "
            f"vin={self.vehicle_vin!r} status={self.status!r}>"
        )
