from fastapi.testclient import TestClient

from logistics_image_service.shipment_events import app, get_images


class RecordingImages:
    def __init__(self) -> None:
        self.calls: list[tuple[bytes, str, str]] = []

    def compress_proof(self, image: bytes, filename: str, event_id: str) -> dict[str, str]:
        self.calls.append((image, filename, event_id))
        return {"id": "proof-42", "format": "webp"}


def test_delivered_event_compresses_proof_and_moves_to_ready() -> None:
    images = RecordingImages()
    app.dependency_overrides[get_images] = lambda: images
    try:
        response = TestClient(app).post(
            "/shipment-events",
            json={
                "event_id": "evt-42",
                "shipment_id": "ship-9",
                "kind": "delivered",
                "proof_filename": "doorstep.jpg",
                "proof_base64": "anBlZw==",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["state"] == "proof_ready"
    assert response.json()["proof"]["id"] == "proof-42"
    assert images.calls == [(b"jpeg", "doorstep.jpg", "evt-42")]


def test_delivered_event_without_proof_becomes_exception() -> None:
    images = RecordingImages()
    app.dependency_overrides[get_images] = lambda: images
    try:
        response = TestClient(app).post(
            "/shipment-events",
            json={"event_id": "evt-43", "shipment_id": "ship-9", "kind": "delivered"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["state"] == "exception"
    assert images.calls == []

