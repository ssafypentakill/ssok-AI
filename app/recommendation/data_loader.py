"""Load recommendation CSVs without mixing evaluation events into training.

Run from the repository root: python -m app.recommendation.data_loader
"""

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "mock"
Row = dict[str, Any]


@dataclass
class RecommendationData:
    products: dict[int, Row]
    users: dict[int, Row]
    interactions: list[Row]


def _integer(value: str) -> int:
    return int(value)


def _optional_integer(value: str) -> int | None:
    return int(value) if value else None


def _boolean(value: str) -> bool:
    if value not in {"true", "false"}:
        raise ValueError("expected 'true' or 'false'")
    return value == "true"


def _timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return result


def _read(path: Path, conversions: dict) -> list[Row]:
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = conversions.keys() - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns: {sorted(missing)}")
        for line, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"{path}:{line}: invalid CSV column count")
            for field, convert in conversions.items():
                try:
                    row[field] = convert(row[field])
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"{path}:{line}: invalid {field}: {exc}") from exc
            rows.append(row)
    return rows


def _index(rows: list[Row], key: str) -> dict[int, Row]:
    indexed = {}
    for row in rows:
        identifier = row[key]
        if identifier <= 0 or identifier in indexed:
            raise ValueError(f"Invalid or duplicate {key}: {identifier}")
        indexed[identifier] = row
    return indexed


def load_recommendation_data(
    data_dir: str | Path = DEFAULT_DATA_DIR,
    *,
    split: str = "train",
) -> RecommendationData:
    """Load one split only. Validation/test require an explicit split argument.

    Keep historical products and inactive users for reference validation.
    Current availability filtering belongs to the recommendation serving step;
    historical evaluation must reconstruct availability at its evaluation time.
    This loader checks input types and references, not all ERD business rules.
    """
    if split not in {"train", "validation", "test"}:
        raise ValueError("split must be train, validation, or test")
    root = Path(data_dir)
    products = _index(_read(root / "products.csv", {
        "product_id": _integer, "price": _integer, "stock": _integer,
        "is_active": _boolean, "created_at": _timestamp,
        "updated_at": _timestamp,
    }), "product_id")
    users = _index(_read(root / "users.csv", {
        "user_id": _integer, "created_at": _timestamp,
    }), "user_id")
    interactions = _read(root / "splits" / f"{split}.csv", {
        "event_id": _integer, "user_id": _integer, "product_id": _integer,
        "interaction_type": str, "timestamp": _timestamp,
        "quantity": _integer, "order_id": _optional_integer,
        "source_id": _integer,
    })
    _index(interactions, "event_id")
    for event in interactions:
        context = f"event_id={event['event_id']}"
        if event["product_id"] not in products:
            raise ValueError(f"{context}: unknown product_id={event['product_id']}")
        if event["user_id"] not in users:
            raise ValueError(f"{context}: unknown user_id={event['user_id']}")
        if event["interaction_type"] not in {"view", "like", "cart", "purchase"}:
            raise ValueError(f"{context}: unknown interaction_type")
        if event["quantity"] <= 0:
            raise ValueError(f"{context}: quantity must be positive")
    interactions.sort(key=lambda event: (event["timestamp"], event["event_id"]))
    return RecommendationData(products, users, interactions)


if __name__ == "__main__":
    data = load_recommendation_data()
    print(f"Products: {len(data.products)}")
    print(f"Users: {len(data.users)}")
    print(f"Train interactions: {len(data.interactions)}")
