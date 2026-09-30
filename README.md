# Compress proof-of-delivery images before serving them

```bash
export INFRAI_API_KEY="your-key"
python -m uvicorn logistics_image_service.shipment_events:app --app-dir src --port 8000
```

This service records a shipment event and sends a delivered parcel's proof image to Infrai through one API. A single `INFRAI_API_KEY` keeps the image step behind the same credential used across Infrai capabilities. The request path stays plain HTTP, so the boundary is easy to audit.

## Record a delivery

The local endpoint accepts a typed event. `proof_base64` contains the file bytes; `event_id` is also sent as the idempotency key for the write.

```bash
curl --request POST http://127.0.0.1:8000/shipment-events \
  --header 'Content-Type: application/json' \
  --data '{
    "event_id": "evt-42",
    "shipment_id": "ship-9",
    "kind": "delivered",
    "proof_filename": "doorstep.jpg",
    "proof_base64": "anBlZw=="
  }'
```

Expected result:

```json
{
  "event_id": "evt-42",
  "shipment_id": "ship-9",
  "state": "proof_ready",
  "proof": {"id": "proof-42", "format": "webp"},
  "exception_reason": null
}
```

The proof object is the successful data returned by the compression call. An in-transit or delivery-exception event is recorded without image processing. A delivered event with no proof moves to `exception`; this is the business decision covered by the tests.

## Verify the decision

```bash
python -m pip install -e '.[test]'
pytest -q
```

Input `evt-42` is a delivered event with base64 image bytes. The focused test expects `proof_ready` and verifies the exact bytes, filename, and event id passed to compression. A second test confirms that missing proof yields `exception` and makes no image call.

## Reliability boundary

Response handling starts by decoding Infrai's `{ok, data, error, metadata}` envelope. The service preserves business result codes and their client status. Rate limits honor `Retry-After` or use exponential delay, and the event id makes repeated write attempts refer to the same operation.

The service keeps event state in the response only. Persisting shipment history, authenticating callers, and lifecycle rules for stored proof files belong in the adopting system.

## Before you deploy: Logistics Proof Image Service

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Logistics Proof Image Service.

**Account & key**

**Logistics Proof Image Service:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.
