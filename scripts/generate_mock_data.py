"""Reproducible recommendation fixtures. Python 3.11+, standard library only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KST = timezone(timedelta(hours=9))
AS_OF = datetime(2026, 10, 27, tzinfo=KST)
START = datetime(2026, 9, 1, tzinfo=KST)
CREATED = datetime(2026, 8, 1, tzinfo=KST)
TRAIN_END = datetime(2026, 10, 17, tzinfo=KST)
VALIDATION_END = datetime(2026, 10, 22, tzinfo=KST)
WEIGHTS = {"view": 1, "like": 3, "cart": 5, "purchase": 10}

# Each tuple: product kind, typical KRW price, embedding-friendly specifications.
CATALOG = {
    "디지털": ("누리텍", "소리온", "모노랩", [
        ("무선 키보드", 59000, "블루투스 저소음 멀티페어링 재택근무 사무용"),
        ("무선 마우스", 29000, "인체공학 무소음 충전식 노트북 사무용"),
        ("무선 이어폰", 79000, "노이즈캔슬링 통화 음악 감상 휴대용"),
        ("보조 배터리", 35000, "10000mAh USB-C 고속충전 여행 출퇴근"),
        ("태블릿 거치대", 25000, "각도 조절 접이식 알루미늄 온라인 강의")]),
    "패션": ("오브데이", "모먼트웨어", "라온핏", [
        ("면 티셔츠", 19000, "면 100% 남녀공용 데일리 기본핏"),
        ("후드 집업", 49000, "면 혼방 남녀공용 간절기 오버핏"),
        ("데일리 백팩", 69000, "노트북 수납 생활방수 출퇴근 여행"),
        ("러닝 스니커즈", 89000, "경량 쿠션 통기성 워킹 운동화"),
        ("코튼 볼캡", 25000, "면 소재 사이즈 조절 야외 데일리")]),
    "리빙": ("온유홈", "룸앤빛", "포근결", [
        ("LED 데스크 조명", 39000, "밝기 조절 독서 공부 책상 USB 전원"),
        ("수납 바스켓", 15000, "적층형 옷장 정리 소품 보관 손잡이"),
        ("메모리폼 베개", 39000, "메모리폼 침실 휴식 분리형 커버"),
        ("데스크 매트", 19000, "방수 논슬립 책상 정리 사무실"),
        ("무릎 담요", 25000, "극세사 세탁 가능 사무실 캠핑 보온")]),
    "주방": ("담음키친", "소담웨어", "쿡모아", [
        ("보온 텀블러", 29000, "스테인리스 500ml 보온 보냉 출퇴근"),
        ("밀폐 용기 세트", 25000, "냉장 보관 음식 보관 BPA-free 3개입"),
        ("논스틱 프라이팬", 39000, "인덕션 호환 28cm 논스틱 간편 요리"),
        ("실리콘 조리도구", 19000, "내열 실리콘 4종 조리도구 세트"),
        ("드립 커피 세트", 49000, "핸드드립 커피 홈카페 유리 서버")]),
    "스포츠": ("무브온", "트레일업", "핏루프", [
        ("요가 매트", 29000, "TPE 6mm 논슬립 홈트레이닝 스트레칭"),
        ("트레이닝 밴드", 15000, "탄성 밴드 3단계 저항 홈트레이닝"),
        ("러닝 벨트", 19000, "휴대폰 수납 생활방수 조깅 야외 운동"),
        ("캠핑 체어", 59000, "접이식 경량 수납가방 야외 캠핑"),
        ("스포츠 물병", 19000, "트라이탄 750ml 손잡이 운동 등산")]),
    "뷰티": ("수풀케어", "온결뷰티", "클린봄", [
        ("보습 크림", 29000, "50ml 세라마이드 보습 무향 데일리 케어"),
        ("클렌징 폼", 15000, "150ml 약산성 세안 데일리 클렌징"),
        ("핸드 크림", 12000, "50ml 시어버터 보습 휴대용"),
        ("선크림", 25000, "50ml SPF50+ PA++++ 자외선 차단"),
        ("헤어 트리트먼트", 19000, "300ml 모발 보습 데일리 헤어 케어")]),
}

SCHEMAS = {
    "erd/product.csv": "id,name,description,brand,category,price,stock_quantity,image,status,created_at,updated_at",
    "erd/user.csv": "id,email,provider,password_hash,provider_user_id,status,created_at,updated_at",
    "erd/cart.csv": "id,created_at,updated_at",
    "erd/cart_item.csv": "id,cart_id,product_id,quantity,created_at,updated_at",
    "erd/orders.csv": "order_id,member_id,order_status,order_datetime,is_deleted,shipping_fee,total_amount,id2,id3",
    "erd/order_item.csv": "id,product_id,quantity,created_at,updated_at,product_name,unit_price,order_id",
    "erd/payments.csv": "id,order_id,member_id,payment_key,amount,status,approved_at,canceled_at,cancel_reason,created_at,updated_at,order_id2",
    "products.csv": "product_id,name,category,brand,price,description,stock,is_active,status,created_at,updated_at,embedding_text",
    "users.csv": "user_id,status,created_at",
    "interactions.csv": "event_id,user_id,product_id,interaction_type,timestamp,quantity,session_id,order_id,source_table,source_id",
    "support/cart_user_mapping.csv": "cart_id,user_id",
    "fixtures/user_preferences.csv": "user_id,scenario,primary_category,secondary_category,min_price,max_price",
}
for split in ("train", "validation", "test"):
    SCHEMAS[f"splits/{split}.csv"] = SCHEMAS["interactions.csv"]


def stamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def generate(seed: int, product_count: int, user_count: int, sessions: int) -> tuple[dict, dict]:
    rng = random.Random(seed)
    tables = {name: [] for name in SCHEMAS}
    categories = list(CATALOG)
    cold_product_count = max(6, product_count // 16)
    cold_user_count = max(1, user_count // 10)
    warm_products = product_count - cold_product_count
    cold_products = list(range(warm_products + 1, product_count + 1))
    cold_users = list(range(user_count - cold_user_count + 1, user_count + 1))
    for pid in range(1, product_count + 1):
        category = categories[(pid - 1) % len(categories)]
        brands = CATALOG[category][:3]
        kind, base, specs = CATALOG[category][3][((pid - 1) // 6) % 5]
        version = ((pid - 1) // 30) + 1
        brand = brands[(version - 1) % 3]
        tier = ("베이직", "스탠다드", "프리미엄")[(version - 1) % 3]
        price = int(base * (0.65, 1.0, 1.65)[(version - 1) % 3] // 100) * 100
        cold = pid in cold_products
        status = "INACTIVE" if not cold and pid % 23 == 0 else "ACTIVE"
        stock = 0 if not cold and pid % 17 == 0 else rng.randint(5, 120)
        created = AS_OF - timedelta(days=1) if cold else CREATED
        updated = AS_OF - timedelta(days=2) if status != "ACTIVE" or stock == 0 else created
        name = f"{brand} {tier} {kind} V{version:02}"
        description = f"{specs}. {tier} 라인으로 구성한 {category} 상품. {brand}의 {kind}."
        p = dict(zip(SCHEMAS["erd/product.csv"].split(","), [pid, name, description,
            brand, category, price, stock, "", status, stamp(created), stamp(updated)]))
        tables["erd/product.csv"].append(p)
        tables["products.csv"].append(dict(product_id=pid, name=name, category=category,
            brand=brand, price=price, description=description, stock=stock,
            is_active=str(status == "ACTIVE").lower(), status=status,
            created_at=p["created_at"], updated_at=p["updated_at"],
            embedding_text=f"{name}. 카테고리: {category}. 브랜드: {brand}. {description}"))

    products = {p["id"]: p for p in tables["erd/product.csv"]}
    preferences = {}
    for uid in range(1, user_count + 1):
        cold = uid in cold_users
        status = "inactive" if uid == user_count else "active"
        tables["erd/user.csv"].append(dict(id=uid, email=f"mock{uid:04}@example.invalid",
            provider="google", password_hash="", provider_user_id=f"synthetic-google-{uid}",
            status=status, created_at=stamp(CREATED), updated_at=stamp(CREATED)))
        tables["users.csv"].append(dict(user_id=uid, status=status, created_at=stamp(CREATED)))
        primary = categories[(uid - 1) % 6]
        secondary = categories[(uid + 1) % 6] if uid % 4 == 0 else ""
        low, high = ((5000, 25000), (15000, 65000), (40000, 180000))[((uid - 1) // 6) % 3]
        scenario = "cold_start" if cold else "multi_interest" if secondary else "focused"
        pref = dict(user_id=uid, scenario=scenario, primary_category=primary,
                    secondary_category=secondary, min_price=low, max_price=high)
        preferences[uid] = pref
        tables["fixtures/user_preferences.csv"].append(pref)
        if not cold:
            tables["erd/cart.csv"].append(dict(id=uid, created_at=stamp(CREATED), updated_at=stamp(CREATED)))
            tables["support/cart_user_mapping.csv"].append(dict(cart_id=uid, user_id=uid))

    def event(uid, pid, kind, when, sid, quantity=1, order_id="", source_table="mock_event", source_id=""):
        eid = len(tables["interactions.csv"]) + 1
        row = dict(event_id=eid, user_id=uid, product_id=pid, interaction_type=kind,
                   timestamp=stamp(when), quantity=quantity, session_id=sid, order_id=order_id,
                   source_table=source_table, source_id=source_id if source_id != "" else eid)
        tables["interactions.csv"].append(row)
        return row

    # Shared category cohorts, soft budgets, popularity and 12% exploratory traffic.
    schedule = []
    for uid in range(1, user_count - cold_user_count + 1):
        for j in range(sessions):
            # Stratification guarantees historical and held-out sessions for each user.
            slot_seconds = 53 * 86400 / sessions
            second = int(j * slot_seconds + rng.random() * (slot_seconds - 600))
            schedule.append((START + timedelta(seconds=second), uid, f"u{uid:04}-s{j + 1:04}"))
    schedule.sort()
    liked = set()
    cart_state = {}
    for when, uid, sid in schedule:
        pref = preferences[uid]
        candidates = list(products.values())[:warm_products]
        weights = []
        for p in candidates:
            category_score = 9 if p["category"] == pref["primary_category"] else 5 if p["category"] == pref["secondary_category"] else 0.3
            price_score = 1.0 if pref["min_price"] <= p["price"] <= pref["max_price"] else 0.2
            popularity = 2 if p["id"] <= 30 else 1
            weights.append(category_score * price_score * popularity)
        picked = []
        for _ in range(rng.randint(1, 3)):
            p = rng.choice(candidates) if rng.random() < 0.12 else rng.choices(candidates, weights=weights, k=1)[0]
            if p not in picked:
                picked.append(p)
        checkout = []
        for index, p in enumerate(picked):
            at = when + timedelta(seconds=index * 60)
            pid = p["id"]
            event(uid, pid, "view", at, sid)
            if rng.random() < 0.20 and (uid, pid) not in liked:
                event(uid, pid, "like", at + timedelta(seconds=10), sid)
                liked.add((uid, pid))
            if rng.random() < 0.30:
                quantity = rng.choices([1, 2, 3], weights=[85, 12, 3], k=1)[0]
                added = event(uid, pid, "cart", at + timedelta(seconds=20), sid, quantity)
                # A cart action sets the current quantity, rather than incrementing it.
                cart_state[(uid, pid)] = added
                if rng.random() < 0.48:
                    checkout.append((p, quantity))
        if not checkout:
            continue
        oid = len(tables["erd/orders.csv"]) + 1
        order_time = when + timedelta(minutes=5)
        paid_time = order_time + timedelta(seconds=30)
        # Deterministic fixtures ensure every state is represented.
        status = ["DELIVERED", "PAID", "DELIVERED", "CANCELLED", "PENDING"][((oid - 1) % 5)]
        subtotal = sum(p["price"] * quantity for p, quantity in checkout)
        shipping = 0 if subtotal >= 50000 else 3000
        tables["erd/orders.csv"].append(dict(order_id=oid, member_id=uid,
            order_status=status, order_datetime=stamp(order_time), is_deleted="false",
            shipping_fee=shipping, total_amount=subtotal + shipping, id2="", id3=uid))
        for p, quantity in checkout:
            iid = len(tables["erd/order_item.csv"]) + 1
            tables["erd/order_item.csv"].append(dict(id=iid, product_id=p["id"], quantity=quantity,
                created_at=stamp(order_time), updated_at=stamp(order_time), product_name=p["name"],
                unit_price=p["price"], order_id=oid))
            if status in {"PAID", "DELIVERED"}:
                event(uid, p["id"], "purchase", paid_time, sid, quantity, oid, "order_item", iid)
            cart_state.pop((uid, p["id"]), None)
        pending = status == "PENDING"
        cancelled = status == "CANCELLED"
        cancel_time = paid_time + timedelta(hours=2)
        tables["erd/payments.csv"].append(dict(id=oid, order_id=oid, member_id=uid,
            payment_key="" if pending else f"mock_payment_{oid:06}", amount=subtotal + shipping,
            status="READY" if pending else "CANCELED" if cancelled else "DONE",
            approved_at="" if pending else stamp(paid_time), canceled_at=stamp(cancel_time) if cancelled else "",
            cancel_reason="MOCK_USER_CANCEL" if cancelled else "", created_at=stamp(order_time),
            updated_at=stamp(cancel_time if cancelled else order_time if pending else paid_time), order_id2=oid))

    for (uid, pid), added in sorted(cart_state.items()):
        tables["erd/cart_item.csv"].append(dict(id=len(tables["erd/cart_item.csv"]) + 1,
            cart_id=uid, product_id=pid, quantity=added["quantity"],
            created_at=added["timestamp"], updated_at=added["timestamp"]))
    for cart in tables["erd/cart.csv"]:
        times = [e["timestamp"] for e in tables["interactions.csv"] if e["user_id"] == cart["id"] and e["interaction_type"] in {"cart", "purchase"}]
        times.extend(o["order_datetime"] for o in tables["erd/orders.csv"] if o["member_id"] == cart["id"])
        cart["updated_at"] = max(times, default=cart["created_at"])
    tables["interactions.csv"].sort(key=lambda e: (e["timestamp"], e["event_id"]))
    for e in tables["interactions.csv"]:
        at = datetime.fromisoformat(e["timestamp"])
        split = "train" if at < TRAIN_END else "validation" if at < VALIDATION_END else "test"
        tables[f"splits/{split}.csv"].append(e.copy())
    metadata = dict(schema_version=1, seed=seed, product_count=product_count, user_count=user_count,
        sessions_per_warm_user=sessions, snapshot_at=stamp(AS_OF), event_start=stamp(START),
        train_end_exclusive=stamp(TRAIN_END), validation_end_exclusive=stamp(VALIDATION_END),
        timezone="Asia/Seoul", currency="KRW", synthetic=True,
        cold_user_ids=cold_users, cold_product_ids=cold_products, suggested_weights=WEIGHTS,
        interaction_counts=dict(Counter(e["interaction_type"] for e in tables["interactions.csv"])),
        category_counts=dict(Counter(p["category"] for p in tables["products.csv"])),
        sources=["ssok.png", "ssok-프로젝트-계획.md"],
        note="ERD-derived CSV fixtures, not a production SQL seed. See README for assumptions.")
    return tables, metadata


def save(output: Path, tables: dict, metadata: dict) -> None:
    files = {}
    for name, rows in tables.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=SCHEMAS[name].split(","), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        files[name] = dict(rows=len(rows), columns=SCHEMAS[name].split(","),
                           sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    metadata["files"] = files
    (output / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "mock")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--products", type=int, default=300)
    parser.add_argument("--users", type=int, default=50)
    parser.add_argument("--sessions", type=int, default=60)
    args = parser.parse_args()
    if args.products < 60 or args.users < 10 or not 20 <= args.sessions <= 5000:
        parser.error("--products >= 60, --users >= 10, 20 <= --sessions <= 5000 are required")
    tables, metadata = generate(args.seed, args.products, args.users, args.sessions)
    save(args.output, tables, metadata)
    from validate_mock_data import validate
    report = validate(args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
