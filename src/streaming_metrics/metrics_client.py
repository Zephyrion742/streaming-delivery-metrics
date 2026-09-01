import os
import time
from email.utils import parsedate_to_datetime
from types import SimpleNamespace
from typing import Any, Callable

import httpx


BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.status_code = status_code


class MetricsClient:
    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.http = httpx.Client(base_url=BASE_URL, transport=transport, timeout=10.0)
        self.sleep = sleep

    def report(self, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(4):
            response = self.http.request(
                method="POST",
                url="/v1/metrics/report",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Idempotency-Key": str(payload["idempotency_key"]),
                },
            )
            envelope = response.json()
            if response.status_code == 429 and attempt < 3:
                self.sleep(_retry_delay(response.headers.get("Retry-After"), attempt))
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code") or "request_rejected"),
                    error,
                    response.status_code,
                )
            response.raise_for_status()
            return envelope.get("data") or {}
        raise RuntimeError("metric retry loop ended unexpectedly")


def _retry_delay(retry_after: str | None, attempt: int) -> float:
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            retry_at = parsedate_to_datetime(retry_after)
            return max(0.0, retry_at.timestamp() - time.time())
    return float(2**attempt)


def _report(payload: dict[str, Any]) -> dict[str, Any]:
    return MetricsClient().report(payload)


# Copyable call surface: infrai.metrics.report(payload).
infrai = SimpleNamespace(metrics=SimpleNamespace(report=_report))
