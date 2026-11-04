"""Populate product_embedding for the local seed_postgres.py catalog."""

import json
import subprocess

from app.recommendation.embeddings import MODEL_NAME, e5_vectors


CATALOG = """
SELECT product_id, concat(product_name, '. 카테고리: ', category, '. 브랜드: ',
                          brand, '. ', description) AS embedding_text
FROM public.product WHERE image_url LIKE '/mock/ssok-reco-v1/%'
"""


def sql(statement):
    result = subprocess.run(
        ["docker", "exec", "-i", "-e", "PGCLIENTENCODING=UTF8", "psql", "sh", "-c",
         'exec psql -X -qAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
        input=statement, stdout=subprocess.PIPE, encoding="utf-8", check=True,
    )
    return result.stdout.strip()


def main():
    rows = sql(f"SELECT row_to_json(p) FROM ({CATALOG}) p ORDER BY product_id;")
    products = {p["product_id"]: p for p in map(json.loads, rows.splitlines())}
    if not products:
        raise SystemExit("목업 상품이 없습니다. 먼저 python scripts/seed_postgres.py 를 실행하세요.")
    vectors = e5_vectors(products)
    # Stage via COPY so database text is never interpolated into SQL.
    data = []
    for pid, vector in vectors.items():
        text_hex = products[pid]["embedding_text"].encode("utf-8").hex()
        values = json.dumps([vector[i] for i in range(384)], allow_nan=False)
        data.append(f"{pid}\t{text_hex}\t{MODEL_NAME}\t{values}")
    result = sql(f"""
BEGIN;
CREATE TEMP TABLE batch (pid bigint, source_hex text, model text, vec vector(384)) ON COMMIT DROP;
COPY batch FROM STDIN;
""" + "\n".join(data) + "\n\\.\n" + f"""
INSERT INTO public.product_embedding AS dest (product_id, embedding, model_name)
SELECT b.pid, b.vec, b.model FROM batch b JOIN ({CATALOG}) p ON p.product_id = b.pid
WHERE encode(convert_to(p.embedding_text, 'UTF8'), 'hex') = b.source_hex
ON CONFLICT (product_id) DO UPDATE SET embedding = excluded.embedding,
    model_name = excluded.model_name, updated_at = now()
WHERE dest.embedding IS DISTINCT FROM excluded.embedding OR dest.model_name <> excluded.model_name;
SELECT count(*) FROM batch b JOIN ({CATALOG}) p ON p.product_id = b.pid
JOIN public.product_embedding e ON e.product_id = b.pid
WHERE encode(convert_to(p.embedding_text, 'UTF8'), 'hex') = b.source_hex
  AND e.embedding = b.vec AND e.model_name = b.model AND vector_dims(e.embedding) = 384;
COMMIT;
""")
    print(f"검증 완료: {result}/{len(products)}개 상품의 384차원 E5 벡터가 일치합니다.")
    if int(result) != len(products):
        raise SystemExit("상품이 변경되었을 수 있습니다. 다시 실행하세요.")


if __name__ == "__main__":
    main()
