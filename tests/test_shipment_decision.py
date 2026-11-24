from src.shipment_decision import ShipmentEvent, decide_action


def test_damaged_delivery_is_held_for_review():
    result = decide_action(ShipmentEvent("S-104", "Driver reports a damaged carton"))
    assert result.state == "exception"
    assert result.needs_review is True
    assert result.reason == "hold shipment and review the delivery note"
