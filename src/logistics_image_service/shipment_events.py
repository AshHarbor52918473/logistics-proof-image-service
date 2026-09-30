from __future__ import annotations

import base64
import binascii
import os
from enum import Enum
from typing import Annotated, Any

import httpx
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from .infrai_images import InfraiError, InfraiImages


class EventKind(str, Enum):
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    DELIVERY_EXCEPTION = "delivery_exception"


class ShipmentEvent(BaseModel):
    event_id: str = Field(min_length=1, max_length=100)
    shipment_id: str = Field(min_length=1, max_length=100)
    kind: EventKind
    proof_filename: str | None = None
    proof_base64: str | None = None


class EventResult(BaseModel):
    event_id: str
    shipment_id: str
    state: str
    proof: dict[str, Any] | None = None
    exception_reason: str | None = None


def get_images() -> InfraiImages:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is required")
    return InfraiImages(api_key)


app = FastAPI(title="Logistics proof image service")


@app.post("/shipment-events", response_model=EventResult)
def record_event(
    event: ShipmentEvent,
    images: Annotated[InfraiImages, Depends(get_images)],
) -> EventResult:
    if event.kind is not EventKind.DELIVERED:
        return EventResult(
            event_id=event.event_id,
            shipment_id=event.shipment_id,
            state="recorded",
        )

    if not event.proof_filename or not event.proof_base64:
        return EventResult(
            event_id=event.event_id,
            shipment_id=event.shipment_id,
            state="exception",
            exception_reason="delivered event needs a proof-of-delivery image",
        )

    try:
        image = base64.b64decode(event.proof_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=422, detail="proof_base64 is invalid") from exc

    try:
        proof = images.compress_proof(image, event.proof_filename, event.event_id)
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="image transport failed") from exc

    return EventResult(
        event_id=event.event_id,
        shipment_id=event.shipment_id,
        state="proof_ready",
        proof=proof,
    )
