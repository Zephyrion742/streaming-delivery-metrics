from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from .delivery_reporter import DeliveryEvent, MetricPoint, report_delivery
from .metrics_client import InfraiError, MetricsClient


app = FastAPI(title="Streaming delivery metrics")


class ReportedMetric(BaseModel):
    event_id: str
    metric_name: str
    metric_type: str
    value: float


def get_reporter() -> MetricsClient:
    return MetricsClient()


@app.post("/delivery-events", response_model=ReportedMetric)
def delivery_event(
    event: DeliveryEvent,
    reporter: MetricsClient = Depends(get_reporter),
) -> ReportedMetric:
    try:
        point: MetricPoint = report_delivery(event, reporter)
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=exc.detail) from exc
    return ReportedMetric(
        event_id=event.event_id,
        metric_name=point.name,
        metric_type=point.type,
        value=point.value,
    )
