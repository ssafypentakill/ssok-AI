"""Validate on-disk CSV relations, recommendation signals and temporal splits."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def date(value):
    result = datetime.fromisoformat(value)
    require(result.utcoffset() is not None, f"Missing timezone: {value}")
    return result


def validate(folder: Path) -> dict:
    from generate_mock_data import SCHEMAS

    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    tables = {}
    for name, schema in SCHEMAS.items():
        with (folder / name).open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            require(reader.fieldnames == schema.split(","), f"Columns: {name}")
            tables[name] = list(reader)
        require(len(tables[name]) == meta["files"][name]["rows"], f"Row count: {name}")
        require(all(None not in row and None not in row.values() for row in tables[name]), f"Malformed row: {name}")

    def index(name, key="id"):
        rows = tables[name]
        result = {r[key]: r for r in rows}
        require(len(result) == len(rows), f"Duplicate key: {name}.{key}")
        require(all(int(k) > 0 for k in result), f"Nonpositive ID: {name}.{key}")
        return result

    products = index("erd/product.csv")
    users = index("erd/user.csv")
    carts = index("erd/cart.csv")
    orders = index("erd/orders.csv", "order_id")
    items = index("erd/order_item.csv")
    cart_items = index("erd/cart_item.csv")
    payments = index("erd/payments.csv")
    events = index("interactions.csv", "event_id")
    ai_products = index("products.csv", "product_id")
    ai_users = index("users.csv", "user_id")
    mappings = index("support/cart_user_mapping.csv", "cart_id")
    prefs = index("fixtures/user_preferences.csv", "user_id")
    require(set(products) == set(ai_products), "Product projection IDs")
    require(set(users) == set(ai_users) == set(prefs), "User projection IDs")
    require(set(carts) == set(mappings), "Cart mapping IDs")
    require(len(products) == meta["product_count"] and len(users) == meta["user_count"], "Configured counts")
    snapshot = date(meta["snapshot_at"])
    for p in products.values():
        require(int(p["price"]) > 0 and int(p["stock_quantity"]) >= 0, "Product price/stock")
        require(p["status"] in {"ACTIVE", "INACTIVE"}, "Product status")
        require(date(p["created_at"]) <= date(p["updated_at"]) <= snapshot, "Product dates")
        require(len(p["name"]) <= 100 and len(p["category"]) <= 100 and len(p["brand"]) <= 100, "ERD text length")
        a = ai_products[p["id"]]
        for field in ("name", "description", "brand", "category", "price", "status", "created_at", "updated_at"):
            require(p[field] == a[field], f"Product projection: {field}")
        require(a["stock"] == p["stock_quantity"], "Stock projection")
        require(a["is_active"] == str(p["status"] == "ACTIVE").lower(), "Active projection")
        require(p["name"] in a["embedding_text"] and p["description"] in a["embedding_text"], "Embedding text")
    require(any(p["status"] == "INACTIVE" for p in products.values()), "Missing inactive fixture")
    require(any(p["stock_quantity"] == "0" for p in products.values()), "Missing out-of-stock fixture")
    require(len({u["email"] for u in users.values()}) == len(users), "Duplicate emails")
    for uid, u in users.items():
        require(u["email"].endswith("@example.invalid") and u["password_hash"] == "", "Synthetic account data")
        require(u["status"] == ai_users[uid]["status"] and u["created_at"] == ai_users[uid]["created_at"], "User projection")
        require(date(u["created_at"]) <= date(u["updated_at"]) <= snapshot, "User dates")
    for mapping in mappings.values():
        require(mapping["user_id"] in users, "Cart user FK")
    pairs = set()
    for item in cart_items.values():
        require(item["cart_id"] in carts and item["product_id"] in products, "Cart item FK")
        require(int(item["quantity"]) > 0, "Cart quantity")
        pair = (item["cart_id"], item["product_id"])
        require(pair not in pairs, "Duplicate current cart item")
        pairs.add(pair)
        require(date(carts[item["cart_id"]]["created_at"]) <= date(item["created_at"]) <= date(item["updated_at"]) <= date(carts[item["cart_id"]]["updated_at"]) <= snapshot, "Cart dates")

    order_items = defaultdict(list)
    for item in items.values():
        require(item["order_id"] in orders and item["product_id"] in products, "Order item FK")
        require(int(item["quantity"]) > 0 and int(item["unit_price"]) > 0, "Order quantity/price")
        require(item["product_name"] == products[item["product_id"]]["name"], "Product snapshot name")
        require(date(orders[item["order_id"]]["order_datetime"]) <= date(item["created_at"]) <= date(item["updated_at"]) <= snapshot, "Order item dates")
        order_items[item["order_id"]].append(item)
    payment_by_order = {}
    for payment in payments.values():
        oid = payment["order_id"]
        require(oid in orders and payment["member_id"] in users, "Payment FK")
        require(oid not in payment_by_order, "Fixture expects one payment per order")
        payment_by_order[oid] = payment
        require(payment["order_id2"] == oid, "ERD duplicate order alias")
        require(payment["member_id"] == orders[oid]["member_id"], "Payment owner")
        require(payment["amount"] == orders[oid]["total_amount"], "Payment total")
        require(date(payment["created_at"]) == date(orders[oid]["order_datetime"]), "Payment creation")
        require(date(payment["created_at"]) <= date(payment["updated_at"]) <= snapshot, "Payment dates")
        state = orders[oid]["order_status"]
        expected = {"PAID": "DONE", "DELIVERED": "DONE", "CANCELLED": "CANCELED", "PENDING": "READY"}
        require(state in expected and payment["status"] == expected[state], "Order/payment status")
        if state == "PENDING":
            require(not payment["approved_at"] and not payment["canceled_at"], "Pending payment timestamps")
        else:
            require(date(payment["created_at"]) <= date(payment["approved_at"]) <= date(payment["updated_at"]), "Approval time")
            if state == "CANCELLED":
                require(date(payment["approved_at"]) <= date(payment["canceled_at"]) == date(payment["updated_at"]), "Cancellation time")
            else:
                require(not payment["canceled_at"], "Completed payment cancellation")
    for oid, order in orders.items():
        require(order["member_id"] in users and order["id3"] == order["member_id"], "Order user FK/alias")
        require(order["id2"] == "", "Shipping FK is intentionally unset")
        require(oid in order_items and oid in payment_by_order, "Order without items/payment")
        subtotal = sum(int(i["quantity"]) * int(i["unit_price"]) for i in order_items[oid])
        require(int(order["total_amount"]) == subtotal + int(order["shipping_fee"]), "Order total")
        require(int(order["shipping_fee"]) == (0 if subtotal >= 50000 else 3000), "Shipping rule")

    seen_views = set()
    seen_carts = set()
    purchase_items = []
    like_pairs = set()
    reconstructed_cart = {}
    # Merge checkout removals and actions to reconcile the current cart snapshot.
    cart_timeline = []
    observed_users, observed_products = set(), set()
    timestamps = []
    for e in tables["interactions.csv"]:
        uid, pid = e["user_id"], e["product_id"]
        require(uid in users and pid in products, "Event user/product FK")
        at = date(e["timestamp"])
        require(date(users[uid]["created_at"]) <= at and date(products[pid]["created_at"]) <= at <= snapshot, "Event before creation/after snapshot")
        require(int(e["quantity"]) > 0, "Event quantity")
        kind = e["interaction_type"]
        require(kind in meta["suggested_weights"], "Unknown event kind")
        key = (uid, pid, e["session_id"])
        if kind == "view":
            seen_views.add(key)
        else:
            require(key in seen_views, "Action without earlier session view")
        if kind == "like":
            require((uid, pid) not in like_pairs, "Repeated like without unlike")
            like_pairs.add((uid, pid))
        if kind == "cart":
            seen_carts.add(key)
            cart_timeline.append((at, 0, uid, pid, e["quantity"]))
        if kind == "purchase":
            require(key in seen_carts, "Purchase without earlier cart event")
            require(e["source_table"] == "order_item" and e["source_id"] in items, "Purchase source FK")
            item = items[e["source_id"]]
            require(item["order_id"] == e["order_id"] and item["product_id"] == pid and item["quantity"] == e["quantity"], "Purchase item linkage")
            order = orders[e["order_id"]]
            require(order["member_id"] == uid and order["order_status"] in {"PAID", "DELIVERED"}, "Non-completed order treated as purchase")
            require(payment_by_order[e["order_id"]]["approved_at"] == e["timestamp"], "Purchase approval time")
            purchase_items.append(e["source_id"])
        else:
            require(e["source_table"] == "mock_event" and e["source_id"] == e["event_id"] and not e["order_id"], "Mock event source")
        observed_users.add(uid)
        observed_products.add(pid)
        timestamps.append(at)
    require(timestamps == sorted(timestamps), "Events must be chronologically sorted")
    expected_items = {iid for iid, item in items.items() if orders[item["order_id"]]["order_status"] in {"PAID", "DELIVERED"}}
    require(len(purchase_items) == len(set(purchase_items)) and set(purchase_items) == expected_items, "Purchase coverage/deduplication")
    for item in items.values():
        order = orders[item["order_id"]]
        cart_timeline.append((date(order["order_datetime"]), 1, order["member_id"], item["product_id"], None))
    for at, priority, uid, pid, quantity in sorted(cart_timeline):
        if priority == 0:
            reconstructed_cart[(uid, pid)] = quantity
        else:
            reconstructed_cart.pop((uid, pid), None)
    actual_cart = {(mappings[i["cart_id"]]["user_id"], i["product_id"]): i["quantity"] for i in cart_items.values()}
    require(actual_cart == reconstructed_cart, "Current cart does not match action/checkout history")
    require(set(users) - observed_users == set(map(str, meta["cold_user_ids"])), "Cold user fixtures")
    require(not observed_products.intersection(map(str, meta["cold_product_ids"])), "Cold product has events")
    for pid in map(str, meta["cold_product_ids"]):
        require(ai_products[pid]["is_active"] == "true" and int(ai_products[pid]["stock"]) > 0, "Cold product not recommendable")
    require(dict(Counter(e["interaction_type"] for e in events.values())) == meta["interaction_counts"], "Event counts metadata")

    train_end, val_end = date(meta["train_end_exclusive"]), date(meta["validation_end_exclusive"])
    split_ids = []
    for split in ("train", "validation", "test"):
        rows = tables[f"splits/{split}.csv"]
        require(rows, f"Empty split: {split}")
        for row in rows:
            require(row["event_id"] in events and row == events[row["event_id"]], "Split row mismatch")
            at = date(row["timestamp"])
            require((split == "train" and at < train_end) or
                    (split == "validation" and train_end <= at < val_end) or
                    (split == "test" and val_end <= at <= snapshot), "Temporal split leakage")
            split_ids.append(row["event_id"])
    require(len(split_ids) == len(set(split_ids)) and set(split_ids) == set(events), "Split overlap/missing rows")
    for name in SCHEMAS:
        require(hashlib.sha256((folder / name).read_bytes()).hexdigest() == meta["files"][name]["sha256"], f"Checksum: {name}")
    return dict(valid=True, products=len(products), users=len(users), interactions=len(events),
                orders=len(orders), order_items=len(items), cart_items=len(cart_items),
                interaction_counts=meta["interaction_counts"], cold_users=len(meta["cold_user_ids"]),
                cold_products=len(meta["cold_product_ids"]),
                splits={s: len(tables[f"splits/{s}.csv"]) for s in ("train", "validation", "test")})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "mock")
    args = parser.parse_args()
    print(json.dumps(validate(args.data_dir), ensure_ascii=False, indent=2))
