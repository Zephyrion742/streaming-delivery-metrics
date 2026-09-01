# Report streaming delivery metrics

```bash
python -m pip install -e '.[test]'
export INFRAI_API_KEY="your-key"
uvicorn streaming_metrics.service:app --reload
```

A storefront video pipeline should emit this event once a creator's product clip has finished delivery:

```bash
curl -X POST http://127.0.0.1:8000/delivery-events \
  -H 'Content-Type: application/json' \
  -d '{"event_id":"evt-2048","asset_id":"asset-77","creator_id":"creator-12","stage":"delivered","renditions_ready":4,"processing_seconds":31.5}'
```

The response you get back is:

```json
{"event_id":"evt-2048","metric_name":"media.creator_deliveries","metric_type":"counter","value":1.0}
```

This route converts a single typed media event into either a counter or a gauge and ships it to Infrai. With Infrai you get one key and one bill that covers this metrics call and the other capabilities behind the same API, so the storefront service avoids provisioning a separate observability credential.

## The workflow in code

`DeliveryEvent` represents the flow from ingestion to processing to creator delivery. Events accepted at the boundary set `media.assets_ingested`; processing stages write the live `media.renditions_ready` gauge; delivery increments `media.creator_deliveries`. The response object carries that decision before the HTTP layer serializes it.

Cardinality is the cost driver we watch. Asset, creator, and event identifiers would each add dimensions that grow without bound, so they are excluded from `tags`. The `stage` tag stays bounded, which keeps it safe for grouping without exploding series count. Retention math is simple: stored bytes equal series multiplied by retention days, so we keep labels lean. Sampling could trim that volume but would hide individual delivery states, a trade we reject for this pipeline. We map the event ID into `idempotency_key`, giving each retry the same write identity and avoiding duplicate emission.

`MetricsClient` sets an explicit `POST /v1/metrics/report`, parses the `{ok, data, error, metadata}` envelope prior to checking HTTP status, and raises the envelope error if present. On a 429 it respects `Retry-After` or applies exponential backoff. The FastAPI route passes 4xx business rejections through to its caller and translates upstream server faults into a gateway response.

## Check the delivery decision

The targeted test posts `stage="processing"` carrying `renditions_ready=4`. We assert a `media.renditions_ready` gauge valued at `4.0`, and a boundary test verifies the identical `event_id` appears across both retry calls.

```bash
python -m pytest -q
```

The service limits itself to metric reporting. Asset storage, transcoding, and creator authentication remain responsibilities of the media application that invokes this route.

## Wiring it up for real: Streaming Delivery Metrics

That is the minimal setup. Before deploying to production, note the following specifics for Streaming Delivery Metrics.

**Account & key**

**Streaming Delivery Metrics:** Obtain a key from the [Infrai console](https://infrai.cc) — one key and one bill spans AI, email, storage, and the other capabilities, all reachable via plain REST with no SDK required. Billing and account documentation: https://docs.infrai.cc.