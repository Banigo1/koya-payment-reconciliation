
#!/usr/bin/env python3

"""Payment reconciliation."""

import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def parse_timestamp(value):
    """Parse ISO timestamps into comparable UTC datetimes."""
    if not isinstance(value, str):
        return None

    try:
        timestamp = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        return timestamp.astimezone(timezone.utc)

    except (ValueError, TypeError):
        return None


def reconcile_payments():
    latest_attempts = {}
    payments_file = BASE_DIR / "payments.jsonl"

    with payments_file.open("r", encoding="utf-8") as file:
        for line in file:
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue

            if not isinstance(event, dict):
                continue

            txn_id = event.get("txn_id")
            timestamp = parse_timestamp(event.get("ts"))

            if txn_id is None or txn_id == "" or timestamp is None:
                continue

            txn_id = str(txn_id)
            previous = latest_attempts.get(txn_id)

            if previous is None or timestamp >= previous[0]:
                latest_attempts[txn_id] = (timestamp, event)

    total = Decimal("0")
    count = 0

    for _, event in latest_attempts.values():
        if event.get("status") != "success":
            continue

        try:
            amount_str = str(event["amount"]).strip().replace(",", "")
            amount = Decimal(amount_str)

            if not amount.is_finite():
                raise InvalidOperation

        except (KeyError, InvalidOperation, TypeError, ValueError) as error:
            raise ValueError(
                f"Invalid amount for transaction "
                f"{event.get('txn_id')}: {event.get('amount')!r}"
            ) from error

        total += amount
        count += 1

    expected_file = BASE_DIR / "expected.txt"

    with expected_file.open("r", encoding="utf-8") as file:
        expected = int(file.read().strip())

    if count != expected:
        print(
            f"Check failed: counted {count} successful payments, "
            f"expected {expected}."
        )
        return

    print(f"Check passed: {count} successful payments.")
    print(f"Your code: KOYA-{round(total)}")


if __name__ == "__main__":
    reconcile_payments()
