import httpx

from logistics_image_service.infrai_images import InfraiImages


def test_compress_proof_sends_json() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.headers["content-type"] == "application/json"
        assert request.read() == b'{"image":{"base64":"anBlZw=="},"idempotency_key":"evt-42","store":false}'
        return httpx.Response(200, json={"ok": True, "data": {"format": "webp"}})

    images = InfraiImages("test-key", transport=httpx.MockTransport(respond))
    try:
        assert images.compress_proof(b"jpeg", "doorstep.jpg", "evt-42") == {"format": "webp"}
    finally:
        images.close()
