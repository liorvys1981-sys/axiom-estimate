"""SQLAlchemy ORM models for AXIOM ESTIMATE."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Estimate(Base):
    """Persisted estimate record."""

    __tablename__ = "estimates"

    estimate_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    client_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    vehicle_vin: Mapped[str] = mapped_column(String(17), nullable=False, index=True)
    vehicle_year: Mapped[int] = mapped_column(Integer, nullable=False)
    vehicle_make: Mapped[str] = mapped_column(String(64), nullable=False)
    vehicle_model: Mapped[str] = mapped_column(String(64), nullable=False)
    damage_description: Mapped[str] = mapped_column(Text, nullable=False)
    photo_urls: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    office_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(
        Enum("pending", "processing", "completed", "failed", name="estimate_status"),
        nullable=False,
        default="pending",
        index=True,
    )
    estimated_total_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
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

    __table_args__ = (
        Index("ix_estimates_client_status", "client_id", "status"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Estimate {self.estimate_id} [{self.status}]>"
