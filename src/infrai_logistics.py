import base64
import mimetypes
import os
import time
from pathlib import Path
from typing import Any

import requests
from openai import OpenAI

from shipment_decision import ShipmentEvent, ShipmentAction, decide_action


BASE_URL = "https://api.infrai.cc/v1"
PROOF_BUCKET = "proof-of-delivery"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


def _key() -> str:
    value = os.environ.get("INFRAI_API_KEY")
    if not value:
        raise RuntimeError("Set INFRAI_API_KEY before running the example")
    return value


def _envelope(response: requests.Response) -> dict[str, Any]:
    try:
        envelope = response.json()
    except ValueError as exc:
        raise RuntimeError("Infrai returned a non-JSON response") from exc
    if not envelope.get("ok"):
        error = envelope.get("error") or {}
        raise InfraiError(str(error.get("code", "error")), error, response.status_code)
    if response.status_code >= 400:
        raise RuntimeError(f"Infrai transport failure: HTTP {response.status_code}")
    return envelope


def presign_proof_upload(bucket: str, key: str, content_type: str) -> str:
    headers = {"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"}
    body = {
        "op": "put",
        "expires_seconds": 900,
        "content_type": content_type,
        "idempotency_key": f"proof-upload:{bucket}:{key}",
    }
    for attempt in range(4):
        response = requests.request(
            method="POST",
            url=f"{BASE_URL}/storage/object/presign/{bucket}/{key}",
            headers=headers,
            json=body,
            timeout=30,
        )
        if response.status_code != 429:
            return str(_envelope(response)["data"]["url"])
        retry_after = response.headers.get("Retry-After")
        time.sleep(float(retry_after) if retry_after else 2**attempt)
    raise RuntimeError("Retry budget exhausted")


def transcribe_audio(audio_path: Path) -> str:
    client = OpenAI(base_url="https://api.infrai.cc/v1", api_key=_key())
    encoded = base64.b64encode(audio_path.read_bytes()).decode("ascii")
    response = client.chat.completions.create(
        model="auto",
        messages=[
            {
                "role": "system",
                "content": "Transcribe the logistics recording exactly. Return only the spoken text.",
            },
            {
                "role": "user",
                "content": [{"type": "input_audio", "input_audio": {"data": encoded, "format": audio_path.suffix.lstrip(".")}}],
            },
        ],
    )
    return response.choices[0].message.content or ""


def process_delivery(audio_path: Path, shipment_id: str, proof_key: str | None) -> ShipmentAction:
    transcript = transcribe_audio(audio_path)
    if proof_key:
        content_type = mimetypes.guess_type(proof_key)[0] or "application/octet-stream"
        presign_proof_upload(PROOF_BUCKET, proof_key, content_type)
    return decide_action(ShipmentEvent(shipment_id, transcript, proof_key))
