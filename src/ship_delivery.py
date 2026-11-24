import argparse
from pathlib import Path

from infrai_logistics import process_delivery


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe one delivery recording and choose its shipment state")
    parser.add_argument("audio", type=Path)
    parser.add_argument("shipment_id")
    parser.add_argument("--proof-key")
    args = parser.parse_args()
    action = process_delivery(args.audio, args.shipment_id, args.proof_key)
    print(f"{args.shipment_id}: {action.state} | review={action.needs_review} | {action.reason}")


if __name__ == "__main__":
    main()
