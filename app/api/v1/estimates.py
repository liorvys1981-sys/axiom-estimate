"""Estimates API endpoints."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter

from app.models.estimate import EstimateRequest, EstimateResponse, EstimateStatus

router = APIRouter(prefix="/api/v1/estimates", tags=["estimates"])


@router.post("", response_model=EstimateResponse, status_code=202)
async def create_estimate(payload: EstimateRequest) -> EstimateResponse:
    """
    Submit a new damage-estimate request.

    The estimate is queued for asynchronous processing by the relevant
    AI Office(s).  The returned ``estimate_id`` can be used to poll for
    status updates (future endpoint).
    """
    return EstimateResponse(
        estimate_id=str(uuid.uuid4()),
        client_id=payload.client_id,
        vehicle_vin=payload.vehicle_vin,
        status=EstimateStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        message="Estimate received and queued for processing",
    )


@router.get("/{estimate_id}", response_model=EstimateResponse)
async def get_estimate(estimate_id: str) -> EstimateResponse:
    """
    Retrieve the current status of an estimate.

    NOTE: In this MVP the data is not persisted.  This endpoint is a
    placeholder that will be backed by a real database in the next
    iteration.
    """
    return EstimateResponse(
        estimate_id=estimate_id,
        client_id="unknown",
        vehicle_vin="00000000000000000",
        status=EstimateStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        message="Persistence not yet implemented — MVP placeholder",
    )
