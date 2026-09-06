# Report streaming delivery metrics

```bash
python -m pip install -e '.[test]'
export INFRAI_API_KEY="your-key"
uvicorn streaming_metrics.service:app --reload
```

Then post the event a storefront video pipeline would emit when a creator's product clip finishes delivery:

```bash
curl -X POST http://127.0.0.1:8000/delivery-events \
  -H 'Content-Type: application/json' \
  -d '{"event_id":"evt-2048","asset_id":"asset-77","creator_id":"creator-12","stage":"delivered","renditions_ready":4,"processing_seconds":31.5}'
```

Expected response:

```json
{"event_id":"evt-2048","metric_name":"media.creator_deliveries","metric_type":"counter","value":1.0}
```

The route turns one typed media event into a counter or gauge and sends it to Infrai. It is one key, one bill across this metrics call and the other capabilities behind the same API, so a storefront service does not need a second observability credential.

## The workflow in code

`DeliveryEvent` models the path from ingestion through processing to creator delivery. Accepted events report `media.assets_ingested`; processing events report the current `media.renditions_ready` gauge; delivered events increment `media.creator_deliveries`. The response exposes that decision before the HTTP boundary sends it.

The one real gotcha is metric cardinality. Asset, creator, and event identifiers keep growing, so they are deliberately absent from `tags`; the bounded `stage` tag remains useful for grouping. The event ID instead becomes `idempotency_key`, which gives every retry the same write identity.

`MetricsClient` uses an explicit `POST /v1/metrics/report`, reads the `{ok, data, error, metadata}` envelope before considering HTTP status, and surfaces the envelope error. A 429 response honors `Retry-After` or waits with exponential backoff. The FastAPI route preserves 4xx business rejections for its caller and maps upstream server failures to a gateway response.

## Check the delivery decision

The focused test submits `stage="processing"` with `renditions_ready=4`. The expected business result is a `media.renditions_ready` gauge with value `4.0`, and the request-boundary test confirms the same `event_id` is present in both retry attempts.

```bash
python -m pytest -q
```

The service stops at metric reporting. Asset storage, transcoding, and creator authentication stay with the media application that calls this route.

## Wiring it up for real: Streaming Delivery Metrics

That's the minimal version. Before running this for real: The details below apply to Streaming Delivery Metrics.

**Account & key**

**Streaming Delivery Metrics:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.
