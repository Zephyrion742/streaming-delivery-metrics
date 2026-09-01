from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, Field


Stage = Literal["accepted", "processing", "delivered"]


class DeliveryEvent(BaseModel):
    event_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    creator_id: str = Field(min_length=1)
    stage: Stage
    renditions_ready: int = Field(ge=0)
    processing_seconds: float = Field(ge=0)


@dataclass(frozen=True)
class MetricPoint:
    name: str
    value: float
    type: Literal["counter", "gauge"]
    tags: dict[str, str]
    idempotency_key: str


class Reporter(Protocol):
    def report(self, payload: dict[str, object]) -> dict[str, object]:
        raise RuntimeError("reporter protocol has no concrete transport")


def choose_metric(event: DeliveryEvent) -> MetricPoint:
    if event.stage == "accepted":
        name, value, metric_kind = "media.assets_ingested", 1.0, "counter"
    elif event.stage == "processing":
        name, value, metric_kind = (
            "media.renditions_ready",
            float(event.renditions_ready),
            "gauge",
        )
    else:
        name, value, metric_kind = "media.creator_deliveries", 1.0, "counter"
    return MetricPoint(
        name=name,
        value=value,
        type=metric_kind,
        tags={"stage": event.stage},
        idempotency_key=event.event_id,
    )


def report_delivery(event: DeliveryEvent, reporter: Reporter) -> MetricPoint:
    point = choose_metric(event)
    reporter.report(
        {
            "name": point.name,
            "value": point.value,
            "type": point.type,
            "tags": point.tags,
            "idempotency_key": point.idempotency_key,
        }
    )
    return point
