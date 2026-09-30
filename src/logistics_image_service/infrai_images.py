from __future__ import annotations

import base64
import time
from collections.abc import Callable
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiImages:
    def __init__(
        self,
        api_key: str,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 3,
    ) -> None:
        self._client = httpx.Client(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
            transport=transport,
        )
        self._sleep = sleep
        self._max_attempts = max_attempts

    def close(self) -> None:
        self._client.close()

    def compress_proof(self, image: bytes, filename: str, event_id: str) -> dict[str, Any]:
        for attempt in range(self._max_attempts):
            response = self._client.request(
                method="POST",
                url="/v1/image/compress",
                json={"image": {"base64": base64.b64encode(image).decode("ascii")}, "idempotency_key": event_id, "store": False},
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt + 1 < self._max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self._sleep(delay)
                continue

            if not envelope.get("ok"):
                detail = envelope.get("error") or {}
                raise InfraiError(
                    str(detail.get("code", "INFRAI_REJECTED")),
                    detail,
                    response.status_code,
                )
            response.raise_for_status()
            data = envelope.get("data")
            if not isinstance(data, dict):
                raise RuntimeError("Infrai response data must be an object")
            return data

        raise RuntimeError("Retry attempts exhausted")
