"""Recommend available products from the shared PostgreSQL database."""

import argparse
import json
import math
import os
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from psycopg.rows import dict_row

from app.recommendation.embeddings import MODEL_NAME
from app.recommendation.recommender import WEIGHTS


# Each current cart item or wishlist entry is one signal, independent of quantity.
SIGNALS = """
    SELECT c.user_id, i.product_id, %(cart)s::integer AS weight
    FROM public.cart AS c JOIN public.cart_item AS i ON i.cart_id = c.id
    WHERE i.quantity > 0
    UNION ALL
    SELECT user_id, product_id, %(like)s::integer FROM public.wishlist
"""


def _connect():
    local_env = Path(__file__).resolve().parents[2] / ".env"
    url = os.environ.get("DATABASE_URL") or dotenv_values(local_env).get("DATABASE_URL")
    if url:
        return psycopg.connect(url, connect_timeout=5)
    settings = dotenv_values(Path(__file__).resolve().parents[3] / "ssok" / ".env")
    return psycopg.connect(host="localhost", port=5432, dbname=settings["POSTGRES_DB"],
                           user=settings["POSTGRES_USER"], password=settings["POSTGRES_PASSWORD"],
                           connect_timeout=5)


def recommend_for_member(member_id: int | None = None, limit: int = 10) -> dict:
    """Rank by similarity first; use popularity only when no personalized items exist."""
    if type(limit) is not int or limit < 1:
        raise ValueError("limit must be a positive integer")
    params = {**WEIGHTS, "member": member_id, "model": MODEL_NAME, "limit": limit}
    profile = [0.0] * 384
    with _connect() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        if member_id is not None:
            cur.execute('SELECT status FROM public."user" WHERE id = %s', (member_id,))
            member = cur.fetchone()
            if member and member["status"] != "ACTIVE":
                raise ValueError("Inactive users cannot request recommendations")
            if member:
                # Out-of-stock and retired items may still describe a member's taste.
                cur.execute(f"""
                    WITH signals AS ({SIGNALS})
                    SELECT s.weight, e.embedding::real[] AS embedding
                    FROM signals s JOIN public.product_embedding e USING (product_id)
                    WHERE s.user_id = %(member)s AND e.model_name = %(model)s
                    """, params)
                for row in cur:
                    for i, value in enumerate(row["embedding"]):
                        profile[i] += row["weight"] * value
        if math.hypot(*profile):
            cur.execute("""
                SELECT p.product_id, p.product_name AS name,
                       1 - (e.embedding <=> %(profile)s::vector) AS similarity,
                       0::float8 AS popularity_score,
                       1 - (e.embedding <=> %(profile)s::vector) AS score
                FROM public.product p JOIN public.product_embedding e USING (product_id)
                WHERE p.status = 'ACTIVE' AND p.stock_quantity > 0
                  AND e.model_name = %(model)s AND vector_norm(e.embedding) > 0
                ORDER BY score DESC, p.product_id LIMIT %(limit)s
                """, {**params, "profile": json.dumps(profile)})
            items = cur.fetchall()
            if items:
                return {"mode": "personalized", "personalization_weight": 1.0, "items": items}

        cur.execute(f"""
            WITH signals AS ({SIGNALS}), popularity AS (
                SELECT product_id, sum(weight) AS points FROM signals GROUP BY product_id
            ), scores AS (
                SELECT p.product_id, p.product_name AS name,
                       coalesce(points::float8 / nullif(max(points) OVER (), 0), 0) AS score
                FROM public.product p LEFT JOIN popularity USING (product_id)
                WHERE p.status = 'ACTIVE' AND p.stock_quantity > 0
            )
            SELECT product_id, name, 0::float8 AS similarity, score AS popularity_score, score
            FROM scores ORDER BY score DESC, product_id LIMIT %(limit)s
            """, params)
        return {"mode": "popular", "personalization_weight": 0.0, "items": cur.fetchall()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--member-id", type=int)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(recommend_for_member(args.member_id, args.limit), ensure_ascii=False, indent=2))
