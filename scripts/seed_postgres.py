"""로컬 Docker PostgreSQL 추천 목업. 실행: python scripts/seed_postgres.py

Python 패키지 설치 불필요. 기본 컨테이너 이름은 팀 compose의 psql.
각 PC에서 동일한 예시 데이터와 관계를 생성하며 PK는 각 DB가 발급한다.
"""

import argparse
import subprocess
import sys


SQL = """
BEGIN;
SET LOCAL lock_timeout = '5s';
-- 같은 시드를 동시에 실행해도 같은 상품/주문이 두 번 생성되지 않게 한다.
SELECT pg_advisory_xact_lock(746230001);
CREATE TEMP TABLE seed_member (tag text PRIMARY KEY, email text UNIQUE) ON COMMIT DROP;
INSERT INTO seed_member VALUES
 ('sport', 'ssok-seed-sport@example.invalid'),
 ('desk',  'ssok-seed-desk@example.invalid'),
 ('mixed', 'ssok-seed-mixed@example.invalid'),
 ('new',   'ssok-seed-new@example.invalid'),
 ('coffee', 'ssok-seed-coffee@example.invalid'),
 ('cook', 'ssok-seed-cook@example.invalid'),
 ('camp', 'ssok-seed-camp@example.invalid'),
 ('weekend', 'ssok-seed-weekend@example.invalid'),
 ('one_like', 'ssok-seed-one-like@example.invalid');

INSERT INTO public."user" (email, provider, provider_user_id, status, created_at, updated_at)
SELECT email, 'MOCK', 'ssok-seed-v1-' || tag, 'ACTIVE', DATE '2026-10-01', DATE '2026-10-01'
FROM seed_member ORDER BY tag ON CONFLICT (email) DO NOTHING;
DO $$ BEGIN
 IF EXISTS (SELECT FROM seed_member s JOIN public."user" u USING (email)
            WHERE u.provider IS DISTINCT FROM 'MOCK'
               OR u.provider_user_id IS DISTINCT FROM ('ssok-seed-v1-' || s.tag))
 THEN RAISE EXCEPTION 'Seed email already belongs to another user'; END IF;
END $$;
CREATE TEMP VIEW seed_users AS
 SELECT s.tag, u.id FROM seed_member s JOIN public."user" u USING (email);

CREATE TEMP TABLE seed_catalog (
 sku text PRIMARY KEY, name text, category text, description text, price bigint,
 stock int, status text
) ON COMMIT DROP;
INSERT INTO seed_catalog VALUES
 ('run', '경량 러닝화', '스포츠', '도로 달리기용 통기성 메시 운동화', 79000, 12, 'ACTIVE'),
 ('trail', '트레일 러닝화', '스포츠', '산길 달리기를 위한 접지력 높은 운동화', 89000, 8, 'ACTIVE'),
 ('socks', '러닝 양말', '스포츠', '장거리 달리기용 쿠션 스포츠 양말', 9000, 30, 'ACTIVE'),
 ('shirt', '러닝 티셔츠', '스포츠', '땀이 빨리 마르는 달리기 운동복', 24000, 15, 'ACTIVE'),
 ('keyboard', '저소음 키보드', '디지털', '사무실 문서 작업용 무선 키보드', 49000, 11, 'ACTIVE'),
 ('mouse', '무선 마우스', '디지털', '사무실 책상용 저소음 마우스', 32000, 10, 'ACTIVE'),
 ('stand', '노트북 받침대', '디지털', '높이 조절이 가능한 책상용 노트북 거치대', 29000, 7, 'ACTIVE'),
 ('pad', '데스크 패드', '디지털', '키보드와 마우스를 놓는 책상 매트', 15000, 20, 'ACTIVE'),
 ('soldout', '품절 러닝화', '스포츠', '품절 제외 확인용 러닝화', 69000, 0, 'ACTIVE'),
 ('deleted', '판매 종료 키보드', '디지털', '삭제 제외 확인용 키보드', 39000, 5, 'DELETED'),
 ('dripper', '도자기 드리퍼', '커피', '핸드드립 원두의 향을 살리는 한 잔용 드리퍼', 27000, 14, 'ACTIVE'),
 ('grinder', '수동 커피 그라인더', '커피', '원두를 일정하게 분쇄하는 휴대용 핸드밀', 59000, 9, 'ACTIVE'),
 ('beans', '에티오피아 원두', '커피', '핸드드립용 꽃향이 나는 라이트 로스트 원두 200g', 18000, 25, 'ACTIVE'),
 ('kettle', '드립 주전자', '커피', '핸드드립 물줄기를 조절하는 가는 주둥이 주전자', 34000, 13, 'ACTIVE'),
 ('pan', '무쇠 프라이팬', '주방', '스테이크를 굽고 채소를 볶는 두꺼운 무쇠 팬', 52000, 9, 'ACTIVE'),
 ('board', '원목 도마', '주방', '채소 손질을 위한 양면 나무 도마', 26000, 14, 'ACTIVE'),
 ('knife', '채소 식도', '주방', '채소를 얇게 써는 스테인리스 주방 칼', 39000, 11, 'ACTIVE'),
 ('pot', '양수 냄비', '주방', '수프와 스튜를 끓이는 뚜껑 달린 냄비', 45000, 18, 'ACTIVE'),
 ('tent', '경량 캠핑 텐트', '캠핑', '백패킹 야영을 위한 방수 이인용 텐트', 159000, 6, 'ACTIVE'),
 ('lantern', '충전식 캠핑 랜턴', '캠핑', '텐트 안을 밝히는 휴대용 야영 조명', 32000, 22, 'ACTIVE'),
 ('bag', '삼계절 침낭', '캠핑', '쌀쌀한 야영지에서 덮는 보온 침낭', 68000, 8, 'ACTIVE'),
 ('mat', '접이식 캠핑 매트', '캠핑', '텐트 바닥 냉기를 차단하는 경량 발포 매트', 19000, 16, 'ACTIVE');

INSERT INTO public.product
 (product_name, brand, category, description, price, stock_quantity, status, image_url, created_at, updated_at)
SELECT name, 'SSOK MOCK', category, description, price, stock, status,
       '/mock/ssok-reco-v1/' || sku || '.png', DATE '2026-10-01', DATE '2026-10-01'
FROM seed_catalog s WHERE NOT EXISTS
 (SELECT FROM public.product p WHERE p.image_url = '/mock/ssok-reco-v1/' || s.sku || '.png')
ORDER BY sku;
CREATE TEMP VIEW seed_products AS
 SELECT s.sku, p.product_id FROM seed_catalog s JOIN public.product p
 ON p.image_url = '/mock/ssok-reco-v1/' || s.sku || '.png';
DO $$ BEGIN
 IF (SELECT count(*) FROM seed_products) <> (SELECT count(*) FROM seed_catalog)
 THEN RAISE EXCEPTION 'Duplicate seed product identifier'; END IF;
END $$;

INSERT INTO public.cart (user_id, created_at, updated_at)
SELECT id, DATE '2026-10-02', DATE '2026-10-02' FROM seed_users WHERE tag NOT IN ('new', 'one_like')
ORDER BY tag ON CONFLICT (user_id) DO NOTHING;
INSERT INTO public.cart_item (cart_id, product_id, quantity, created_at, updated_at)
SELECT c.id, p.product_id, x.qty, DATE '2026-10-02', DATE '2026-10-02'
FROM (VALUES ('sport','run',1), ('sport','socks',2), ('desk','keyboard',1),
             ('desk','mouse',1), ('mixed','shirt',1),
             ('coffee','grinder',1), ('coffee','beans',2), ('cook','pan',1), ('cook','board',1),
             ('camp','tent',1), ('camp','lantern',1), ('weekend','beans',1), ('weekend','lantern',1)) AS x(tag,sku,qty)
JOIN seed_users u USING (tag) JOIN public.cart c ON c.user_id = u.id
JOIN seed_products p USING (sku)
ON CONFLICT (cart_id, product_id) DO NOTHING;
INSERT INTO public.wishlist (user_id, product_id)
SELECT u.id, p.product_id
FROM (VALUES ('sport','trail'), ('sport','soldout'), ('desk','stand'),
             ('desk','deleted'), ('mixed','pad'), ('coffee','dripper'), ('coffee','kettle'),
             ('cook','knife'), ('cook','pot'), ('camp','bag'), ('camp','mat'),
             ('weekend','dripper'), ('weekend','bag'), ('one_like','beans')) AS x(tag,sku)
JOIN seed_users u USING (tag) JOIN seed_products p USING (sku)
ON CONFLICT (user_id, product_id) DO NOTHING;

-- 주문과 결제만 연결한다. 현재 Java 스키마에는 주문상품 관계가 없다.
INSERT INTO public.orders (member_id, order_status, is_deleted, order_datetime, recipient_name,
 recipient_phone, postal_code, address, address_detail, shipping_fee, total_amount)
SELECT u.id, x.status, false, DATE '2026-10-03', '테스트 회원', '01000000000',
 '00000', '테스트 주소', 'ssok-reco-v1/' || u.tag, 0, x.amount
FROM (VALUES ('sport','PAID',79000), ('desk','CANCELED',49000)) AS x(tag,status,amount)
JOIN seed_users u USING (tag)
WHERE NOT EXISTS (SELECT FROM public.orders o WHERE o.member_id = u.id
                  AND o.address_detail = 'ssok-reco-v1/' || u.tag);
INSERT INTO public.payments (order_id, member_id, amount, status, payment_key,
 approved_at, canceled_at, created_at, updated_at)
SELECT o.order_id, u.id, o.total_amount,
 CASE WHEN o.order_status = 'PAID' THEN 'APPROVED' ELSE 'CANCELED' END,
 'ssok-reco-v1/' || u.tag, DATE '2026-10-03',
 CASE WHEN o.order_status = 'CANCELED' THEN DATE '2026-10-04' END,
 DATE '2026-10-03', CASE WHEN o.order_status = 'CANCELED' THEN DATE '2026-10-04' ELSE DATE '2026-10-03' END
FROM public.orders o JOIN seed_users u ON o.member_id = u.id
WHERE o.address_detail = 'ssok-reco-v1/' || u.tag
ON CONFLICT (order_id) DO NOTHING;

SELECT u.tag AS scenario, u.id AS member_id,
 (SELECT count(*) FROM public.cart c JOIN public.cart_item i ON i.cart_id = c.id
  WHERE c.user_id = u.id) AS cart_items,
 (SELECT count(*) FROM public.wishlist w WHERE w.user_id = u.id) AS wishlist_items
FROM seed_users u ORDER BY u.tag;
COMMIT;
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", default="psql", help="로컬 PostgreSQL 컨테이너 이름")
    args = parser.parse_args()
    try:
        result = subprocess.run(
            ["docker", "exec", "-i", "-e", "PGCLIENTENCODING=UTF8", args.container,
             "sh", "-c", 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
            input=SQL.encode("utf-8"),
        )
    except FileNotFoundError:
        sys.exit("Docker CLI를 찾을 수 없습니다. Docker Desktop 설치를 확인하세요.")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
