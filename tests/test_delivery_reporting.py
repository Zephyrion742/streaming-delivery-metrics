import httpx

from streaming_metrics.delivery_reporter import DeliveryEvent, choose_metric
from streaming_metrics.metrics_client import MetricsClient


def test_processing_event_reports_ready_renditions_as_a_gauge() -> None:
    event = DeliveryEvent(
        event_id="evt-processing-9",
        asset_id="asset-9",
        creator_id="creator-3",
        stage="processing",
        renditions_ready=4,
        processing_seconds=18.25,
    )

    point = choose_metric(event)

    assert point.name == "media.renditions_ready"
    assert point.type == "gauge"
    assert point.value == 4.0
    assert point.tags == {"stage": "processing"}


def test_rate_limit_retry_keeps_the_event_identity() -> None:
    seen_keys: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_keys.append(request.headers["Idempotency-Key"])
        if len(seen_keys) == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "0"},
                json={"ok": False, "data": None, "error": {"code": "busy"}, "metadata": {}},
            )
        return httpx.Response(
            200,
            json={"ok": True, "data": {"accepted": True}, "error": None, "metadata": {}},
        )

    client = MetricsClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )
    payload = {
        "name": "media.creator_deliveries",
        "value": 1,
        "type": "counter",
        "tags": {"stage": "delivered"},
        "idempotency_key": "evt-delivery-22",
    }

    assert client.report(payload) == {"accepted": True}
    assert seen_keys == ["evt-delivery-22", "evt-delivery-22"]
