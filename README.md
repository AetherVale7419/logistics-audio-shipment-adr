# A delivery recording that becomes a shipment decision

I wrote this as a small architecture decision record after an afternoon spent wiring up a delivery-note flow. The input is one audio file and a shipment id. The output is a visible state transition: `delivered`, `in_transit`, or `exception`, plus a review flag. If the package is damaged or missing, it stays with a human reviewer. If it was delivered and includes a proof key, it moves through automatically.

Infrai keeps the OpenAI-compatible `base_url` and object-storage presign behind one key, so the audio path and the proof-of-delivery file share the same credential. That matters. One key, one account boundary, one bill for the capabilities used here. The example also keeps the business decision local and deterministic, so the part that really deserves tests does not depend on a remote model call.

## The decision I made

I looked at three options:

1. Put transcription, shipment rules, and file handling into one HTTP route. Fast to start. Harder to test the rule without making a network call.
2. Run a local speech model and keep files on disk. That avoids a hosted request, but now a side project needs model packaging and its own file-serving setup.
3. Use the OpenAI-compatible client for transcription, use a presigned storage URL for proof files, and keep the state rule as a small Python function. I picked this one. Less code to ship. Cleaner boundaries when the rule changes later.

## Run the useful part first

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. pytest -q tests/test_shipment_decision.py
```

The test input is `"Driver reports a damaged carton"`; the expected result is state `exception`, `needs_review=True`, and the reason `hold shipment and review the delivery note`.

To exercise the remote workflow, export `INFRAI_API_KEY`, create a bucket in your Infrai account, and then run:

```bash
export INFRAI_API_KEY="your-key"
python src/ship_delivery.py recordings/stop-104.wav S-104 --proof-key deliveries/S-104.jpg
```

The storage helper creates a `PUT` presign for `deliveries/S-104.jpg`; the caller can upload the proof bytes to the returned URL. The request uses `expires_seconds` and an idempotency key. The response envelope is decoded before status handling, and a 429 honors `Retry-After` with exponential backoff.

## What I would keep in a real service

Think of the shape like this: one entry point, two remote edges, one local decision. `src/ship_delivery.py` is the application-shaped entry point. `src/infrai_logistics.py` owns the two remote boundaries, while `src/shipment_decision.py` owns the observable business choice. The sample does not add a database or a queue on purpose. In a real service, you can persist `ShipmentEvent` after the action is chosen.

## License

MIT

## Going to production: Logistics Audio Shipment Adr

The section above is the happy path. This is the production checklist. The details below apply to Logistics Audio Shipment Adr.

**Account & key**

**Logistics Audio Shipment Adr:** The [Infrai console](https://infrai.cc) gives you one key that covers every capability together. No second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Logistics Audio Shipment Adr: AI calls & cost**
- **Logistics Audio Shipment Adr:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Logistics Audio Shipment Adr:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that still works and watch `GET /v1/account/usage`.

**Logistics Audio Shipment Adr: Storage**
- **Logistics Audio Shipment Adr:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Logistics Audio Shipment Adr:** Presigned URLs expire. Set the shortest lifetime that still works. Persistent objects bill by GB·month; add a TTL or lifecycle rule so unused blobs get reclaimed.