# ssok 추천 시스템 목업 데이터

`ssok.png` ERD와 `ssok-프로젝트-계획.md`의 Mock 데이터 계획을 기준으로 만든 **합성 데이터**다. 상품·회원·주문 ID를 연결해서 콘텐츠 기반 추천, 행동 기반 추천, 신규 사용자 처리와 후보 필터를 개발할 수 있다. 기준 시각은 **2026-10-27 00:00:00 Asia/Seoul**이다.

## 바로 사용할 파일

| 파일 | 기본 건수 | 용도 |
| --- | ---: | --- |
| `products.csv` | 300 | 상품 설명 임베딩, 카테고리·브랜드·가격·재고 필터 |
| `users.csv` | 50 | 실제 ERD의 회원 ID와 상태를 반영한 추천용 회원 목록 |
| `interactions.csv` | 8,441 | 조회 5,400 / 좋아요 948 / 장바구니 1,609 / 유효 구매 484 |
| `splits/train.csv` | 7,312 | 초기 학습 및 사용자 프로필 생성 |
| `splits/validation.csv` | 783 | 가중치·파라미터 조정용 이후 행동 |
| `splits/test.csv` | 346 | 최종 동작 평가용 이후 행동 |

건수는 기본 옵션 `seed=42, products=300, users=50, sessions=60` 기준이다. 옵션을 바꿨다면 `metadata.json`의 건수를 확인한다. CSV 15개는 UTF-8 BOM 형식이고, Python에서는 `encoding="utf-8-sig"`로 읽는다. CSV의 빈 값은 NULL/해당 없음, 금액은 정수 원(KRW), 불리언은 `true`/`false`, 시각은 `+09:00`을 포함한 ISO 8601이다. ID는 정수이며 모든 파일에서 같은 대상을 가리킨다.

[엑셀 확인본](../../outputs/mock-20261027/recommendation-mock.xlsx)에는 주요 세 파일의 전체 행이 들어 있다. 날짜 셀은 KST 시각으로 표시한다. 이 파일은 제공 시점의 확인본이므로 Python 생성기로 CSV를 재생성해도 자동으로 갱신되지 않는다. 추천 코드에서는 CSV를 읽는다.

### products.csv

| 컬럼 | 타입 | 의미 / ERD 매핑 |
| --- | --- | --- |
| product_id | int | `product.id` |
| name, category, brand, description | str | `product`의 동일 이름 컬럼 |
| price | int | `product.price`, 원 단위 |
| stock | int | `product.stock_quantity` |
| is_active | bool 문자열 | `product.status == 'ACTIVE'`. 품절 여부는 별도로 확인 |
| status | str | `ACTIVE` 또는 `INACTIVE`, 목업에서 가정한 상태값 |
| created_at, updated_at | ISO 8601 | `product`의 생성·변경 시각 |
| embedding_text | str | 이름·카테고리·브랜드·설명 결합. 임베딩 모델 입력용 파생값 |

숫자 가격과 재고를 임베딩 문자열에 넣지 않았다. 가격 범위는 숫자 조건으로, 판매 가능 여부는 상태·재고 조건으로 필터링한다. 가상 브랜드 18개, 디지털·패션·리빙·주방·스포츠·뷰티 6개 카테고리, 30개 상품 종류에 가격대별 변형이 있다. 판매 중단과 품절 상품은 과거에는 구매 가능했고 10월 25일에 현재 상태로 변경되었다고 가정했다. 이미지는 ERD 컬럼을 유지하되 빈 값이다.

### users.csv

`user_id`는 `user.id`, `status`는 `active`/`inactive`, `created_at`은 가입 시각이다. **ERD에 없는 나이·성별을 임의로 회원 필드에 추가하지 않았다.** 행동을 만든 관심사와 예산은 별도의 검증용 fixture에만 있다. 회원 50번은 비활성 상태이며, 개인화 요청 대상으로 제외하는 시나리오에 사용한다.

### interactions.csv

| 컬럼 | 타입 | 의미 |
| --- | --- | --- |
| event_id | int | 이벤트 고유 ID. 중복 적재 제거용 |
| user_id, product_id | int | `user.id`, `product.id` 참조 |
| interaction_type | str | `view`, `like`, `cart`, `purchase` |
| timestamp | ISO 8601 | 이벤트 발생 시각, 파일은 시간순 정렬 |
| quantity | int | 조회·좋아요는 1, 장바구니·구매는 상품 개수 |
| session_id | str | 같은 방문에서 일어난 행동 묶음 |
| order_id | int 또는 빈 값 | 구매 이벤트의 `orders.order_id` |
| source_table | str | 구매는 `order_item`, 그 외는 가상 이벤트 원천인 `mock_event` |
| source_id | int | 구매는 `order_item.id`, 그 외는 `event_id` |

한 세션에서 조회 후 좋아요·장바구니·구매가 이어질 수 있다. 좋아요 취소는 생성하지 않으며 같은 회원·상품의 좋아요는 한 번만 기록한다. `cart` 이벤트는 해당 상품의 장바구니 수량을 **설정**하는 행동이고, 주문 생성 시 현재 장바구니에서 제거한다. 장바구니 재추가와 같은 상품의 재구매는 가능하다.

구매 신호는 `orders.order_status ∈ {PAID, DELIVERED}`이고 `payments.status == DONE`인 주문상품에서 **주문상품당 1건** 생성한다. 시각은 결제 승인 시각이며 수량은 주문상품과 같다. 취소·미결제 주문에는 구매 신호를 만들지 않는다. 구매 이벤트와 주문상품을 동시에 집계하면 이중 계산이 되므로 하나를 선택한다.

## ERD 기반 파일과 명시적인 가정

실제 SQL DDL, NOT NULL, 상태 enum 정의는 폴더에 없었다. `erd/`는 그림에 나온 컬럼명을 유지한 **추천 개발용 CSV**이며, 운영 DB에 그대로 넣는 SQL seed가 아니다.

| 파일 | 기본 건수 | 관계 / 처리 |
| --- | ---: | --- |
| `erd/product.csv` | 300 | 그림의 상품 컬럼 11개 유지 |
| `erd/user.csv` | 50 | 그림의 회원 컬럼 8개 유지. 가상 OAuth 회원, 비밀번호 NULL |
| `erd/cart.csv` | 45 | 그림에 회원 FK가 없어 원본에는 추가하지 않음 |
| `erd/cart_item.csv` | 645 | 현재 장바구니 상태. `cart_id`, `product_id` FK |
| `erd/orders.csv` | 723 | 회원·주문금액·주문상태. 상품 합계 + 배송비 = 총액 |
| `erd/order_item.csv` | 801 | `order_id`, `product_id` FK와 주문 시점 이름·가격 |
| `erd/payments.csv` | 723 | 주문당 결제 1개. 결제금액 = 주문 총액 |
| `support/cart_user_mapping.csv` | 45 | **ERD에 없는 목업 보조 관계**. `cart_id → user_id` |
| `fixtures/user_preferences.csv` | 50 | **생성·검증 전용** 관심사·예산·시나리오 |

확정되지 않은 부분은 다음과 같이 처리했다.

- **회원 연결:** 추천용 `user_id`, 주문·결제의 `member_id`, ERD의 `user.id`를 같은 내부 회원 ID로 가정했다.
- **중복처럼 보이는 FK:** 그림의 `orders.id3`는 `member_id`, `payments.order_id2`는 `order_id`와 같은 값으로 채웠다. 이는 그림의 관계를 해석한 목업 가정이며 백엔드의 확정 모델이 아니다.
- **배송지:** `orders.id2`는 그림의 배송지 참조 컬럼으로 보이지만 추천에 불필요해 빈 값으로 두었다. `shipping_address`, `email_verification`, `payment_attempts`는 생성 범위에서 제외했다. 배송지 FK가 필수인 실제 DB에 적재하려면 배송지 및 연결 값을 먼저 추가해야 한다.
- **장바구니 소유자:** 실제 연동에서는 `cart.user_id` 같은 FK나 인증된 이벤트의 `user_id`가 필요하다. `support/cart_user_mapping.csv`는 이 연결을 목업에서만 보충한다.
- **조회·좋아요:** ERD에 테이블이 없어 합성 이벤트로 만들었다. 장바구니 이벤트 이력도 현재 상태 테이블과 분리했다. 실제 서비스에서는 별도 행동 로그/API 계약이 필요하다.
- **상태값:** 상품 `ACTIVE/INACTIVE`, 회원 `active/inactive`, 주문 `PAID/DELIVERED/CANCELLED/PENDING`, 결제 `DONE/CANCELED/READY`는 목업에서 선택한 값이다. 주문 취소와 결제 취소의 철자도 서로 다르므로 백엔드 enum과 명시적으로 매핑한다.
- **주문·결제:** 배송비는 상품 합계 50,000원 이상이면 0원, 미만이면 3,000원이다. 할인·부분 취소·부분 환불·결제 재시도·가격 변동은 모델링하지 않았다. 취소 주문은 승인 후 2시간 뒤 전액 취소, PENDING은 미승인 상태다. 긴 기간의 PENDING도 필터 검증을 위해 남겨 둔 상태 fixture다.
- **재고:** `stock_quantity`는 10월 27일 현재 스냅샷이다. 초기 재고·입고·출고 원장은 없으므로 누적 구매 수량에서 역산하는 재고 테스트에는 사용하지 않는다.
- **개인정보·상품 정보:** 이메일은 예약 도메인 `example.invalid`, OAuth 식별자·결제 키·브랜드·상품 설명은 합성값이다. 로그인이나 실제 결제에 사용할 수 없다.

## 추천 구현에 사용하는 방법

1. `products.csv`의 `embedding_text`로 TF-IDF 또는 문장 임베딩을 만든다.
2. `splits/train.csv`에서 사용자별 상품 행동을 집계한다. 시작용 가중치는 조회 1 / 좋아요 3 / 장바구니 5 / 구매 10이며 `metadata.json`에도 있다. 필수 알고리즘은 아니므로 검증 결과에 따라 조정한다.
3. 사용자별 선호 상품 벡터를 가중 평균하거나, 사용자·상품 행렬을 만들어 협업 필터링에 사용한다. 반복 조회 상한, 최근성 감쇠, 구매 수량 반영 여부는 추천 로직에서 결정한다.
4. 현재 추천 후보는 `is_active == true`이고 `stock > 0`인 상품으로 제한한다. 비활성 회원의 요청 처리도 별도로 확인한다. 이미 본 상품·구매 상품 제외는 서비스 정책에 따라 적용한다.
5. 행동이 없는 사용자는 학습 데이터로 계산한 인기 상품이나 카테고리별 대표 상품으로 시작한다. 인기 순위에 validation/test 행동을 미리 넣지 않는다.

Python 표준 라이브러리로 읽는 예시 (`ssok-AI` 폴더에서 실행):

```python
import csv
from pathlib import Path

root = Path("data/mock")
def read_csv(name):
    with (root / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

products = read_csv("products.csv")
users = read_csv("users.csv")
history = read_csv("splits/train.csv")
candidates = [p for p in products if p["is_active"] == "true" and int(p["stock"]) > 0]
# int(row["user_id"]), int(row["product_id"]), int(row["price"]) 등 명시적으로 변환한다.
# bool("false")는 True이므로 불리언 문자열을 bool()로 직접 변환하지 않는다.
```

### 시나리오

- **회원 1~45:** 같은 관심 카테고리를 공유하는 사용자군, 세 가지 가격대, 약 12%의 임의 탐색 행동. 모든 행동이 선호와 정확히 일치하도록 만들지 않았다.
- **4의 배수인 활동 회원:** 두 카테고리에 관심이 있는 복합 취향.
- **회원 46~50:** 행동 이력이 없는 신규 사용자 시나리오. 50번은 비활성 회원이므로 실제 추천 대상인 신규 활성 회원은 46~49번이다. 가입 직후를 뜻하는 것이 아니라 행동이 없다는 의미다.
- **상품 283~300:** 10월 26일 등록되었고 행동 이력이 없는 신규 상품. 현재 판매 가능하고 재고가 있다.
- **기존 상품 중 ID가 17의 배수:** 현재 품절. **23의 배수:** 현재 판매 중단. 두 조건이 겹칠 수도 있다.
- **취소·미결제 주문:** 구매 신호로 잘못 들어가지 않는지 확인한다.

`fixtures/user_preferences.csv`는 목업 생성의 정답을 드러내는 파일이므로 **모델 입력에 넣지 않는다.** 선호 경향을 확인하거나 시연 사용자를 고르는 데만 사용한다.

### 시간 분할과 평가 범위

| 분할 | 이벤트 시각, KST |
| --- | --- |
| train | 2026-09-01 이상 ~ 2026-10-17 미만 |
| validation | 2026-10-17 이상 ~ 2026-10-22 미만 |
| test | 2026-10-22 이상 ~ 기준 시각 이하. 실제 마지막 방문은 10월 23일 |

이벤트 ID 기준으로 세 파일은 중복 없이 전체 이력을 정확히 나눈다. 구매만 평가 라벨로 쓴다면 각 분할에서 `purchase`를 골라 사용하고, 양성 라벨이 없는 회원 수는 따로 보고한다. 같은 상품의 재구매가 가능하므로 신규 상품 발견 평가에서는 학습에서 이미 구매한 항목을 평가 라벨에서도 제외해야 한다.

상품 파일의 상태·재고와 장바구니·주문·결제 파일은 **최종 스냅샷**이다. 과거 시점 평가에 이 현재 상태를 사용하면 미래 정보가 섞일 수 있다. 이 목업의 가정 아래 과거 후보는 `created_at <= 평가시각`으로 제한하고, 10월 25일 이전 기존 상품은 판매 가능했다고 처리한다. 상태 변경 이력·가격 이력을 일반적으로 재현하는 데이터는 아니다. 취소 주문은 모두 10월 24일 이전에 취소되어 위 분할의 최종 스냅샷 이전에 확정된다.

합성 데이터의 Recall/NDCG는 파이프라인 점검용이다. 실제 사용자 선호나 추천 품질을 입증하지 않는다. 노출 로그와 진짜 부정 피드백은 없으므로 미관측 상품을 모두 싫어하는 상품으로 해석하지 않는다.

## 재생성·검증

Python 3.11 이상, 외부 패키지 설치 없이 실행한다. `ssok-AI` 폴더 기준:

```powershell
python scripts/generate_mock_data.py
python scripts/validate_mock_data.py
python -m unittest discover -s tests -v

# 다른 규모는 별도 폴더에 생성
python scripts/generate_mock_data.py --products 500 --users 50 --sessions 100 --seed 42 --output data/mock_500
```

같은 옵션이면 CSV와 metadata가 바이트 단위로 재현된다. 재생성은 지정 출력 폴더의 알려진 CSV 15개와 `metadata.json`을 덮어쓴다. README와 다른 파일은 수정하지 않는다. `products >= 60`, `users >= 10`, `20 <= sessions <= 5000`을 지원한다. 대규모 부하 테스트용 고성능 생성기는 아니며, 먼저 작은 규모로 추천 기능을 개발하는 용도다.

검증기는 헤더·행 수·중복 키·FK·타임스탬프·상품 파생 컬럼·주문 합계·결제 상태·구매 원본 연결·현재 장바구니 재구성·콜드 스타트·시간 분할·SHA-256을 확인한다. 테스트는 잘못된 FK, 취소 주문의 구매 이벤트, 미래 이벤트의 학습 유입, 잘못된 헤더를 의도적으로 넣어 실패가 감지되는지도 확인한다.
