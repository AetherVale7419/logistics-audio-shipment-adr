from dataclasses import dataclass


@dataclass(frozen=True)
class ShipmentEvent:
    shipment_id: str
    transcript: str
    proof_key: str | None = None


@dataclass(frozen=True)
class ShipmentAction:
    state: str
    needs_review: bool
    reason: str


def decide_action(event: ShipmentEvent) -> ShipmentAction:
    text = event.transcript.lower()
    if "damaged" in text or "missing" in text or "exception" in text:
        return ShipmentAction("exception", True, "hold shipment and review the delivery note")
    if "delivered" in text and event.proof_key:
        return ShipmentAction("delivered", False, "attach proof of delivery")
    return ShipmentAction("in_transit", False, "keep shipment moving")
