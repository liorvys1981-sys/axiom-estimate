"""Pydantic models for the Estimates domain."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EstimateStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class EstimateRequest(BaseModel):
    """Payload for creating a new estimate."""

    client_id: str = Field(..., description="Unique identifier for the client shop")
    vehicle_vin: str = Field(..., min_length=17, max_length=17, description="Vehicle VIN")
    vehicle_year: int = Field(..., ge=1900, le=2100)
    vehicle_make: str = Field(..., min_length=1, max_length=64)
    vehicle_model: str = Field(..., min_length=1, max_length=64)
    damage_description: str = Field(..., min_length=1, max_length=2048)
    photo_urls: list[str] = Field(default_factory=list, max_length=20)
    office_ids: list[int] = Field(
        default_factory=lambda: [1],
        description="Which AI offices to involve (1-7)",
    )

    model_config = {"json_schema_extra": {
        "example": {
            "client_id": "shop-001",
            "vehicle_vin": "1HGBH41JXMN109186",
            "vehicle_year": 2022,
            "vehicle_make": "Honda",
            "vehicle_model": "Civic",
            "damage_description": "Front bumper and hood damage from collision",
            "photo_urls": ["https://storage.example.com/photo1.jpg"],
            "office_ids": [1, 2],
        }
    }}


class EstimateResponse(BaseModel):
    """Response returned after creating an estimate."""

    estimate_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str
    vehicle_vin: str
    status: EstimateStatus = EstimateStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    estimated_total_usd: Optional[float] = None
    message: str = "Estimate received and queued for processing"
