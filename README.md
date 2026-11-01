# ssok AI

개인화 상품 추천 기능을 개발하기 위한 초기 저장소입니다.

## 추천용 목업 데이터

`data/mock/`에 상품 300개, 회원 50명, 행동 8,441건과 연결된 주문·결제·장바구니 CSV가 있습니다. [데이터 설명과 ERD 매핑](data/mock/README.md)을 먼저 확인하세요.

Python 3.11 이상에서 외부 패키지 없이 재생성·검증할 수 있습니다.

```powershell
python scripts/generate_mock_data.py
python scripts/validate_mock_data.py
python -m unittest discover -s tests -v
```

추천 입력은 `products.csv`, `users.csv`, `splits/train.csv`를 사용합니다. `fixtures/user_preferences.csv`는 생성 규칙 확인용이며 학습 입력에서 제외합니다. `erd/`는 ERD 기반 CSV로, 확정 DDL에 직접 적재하는 SQL seed는 아닙니다.

## 추천 실행 및 테스트

외부 패키지 없이 Python 표준 라이브러리로 실행합니다.

```powershell
# 비로그인: 인기 추천
python -m app.recommendation.recommender

# 행동이 없는 회원: 인기 추천
python -m app.recommendation.recommender --user-id 46 --limit 5

# 행동이 있는 회원: TF-IDF 개인화 + 인기 추천
python -m app.recommendation.recommender --user-id 1 --limit 5

# 추천 기능 테스트만 실행
python -m unittest discover -s tests -p test_recommender.py -v

# 전체 테스트
python -m unittest discover -s tests -v
```

`Mode: popular`은 인기 추천, `Mode: personalized`는 개인화가 반영된 추천입니다.
`personalization`은 최종 점수에서 개인화 점수가 차지하는 비중입니다.

`app/recommendation/data_loader.py`가 기본적으로 train 데이터만 읽고,
`app/recommendation/recommender.py`가 상품 텍스트의 TF-IDF 벡터와 행동 가중치
(조회 1 / 좋아요 3 / 장바구니 5 / 구매 10)로 추천합니다.
사용자·상품·행동 종류별 반복 횟수는 최대 3회까지 반영하며, 수량은 가중하지 않습니다.
개인화 비중은 누적 행동 점수 / 10으로 계산하고 최대 80%로 제한합니다.
나머지는 후보 내 최대 인기 점수로 정규화한 인기 점수입니다.
이 비중과 가중치는 초기 규칙이며 validation으로 최적화한 값은 아닙니다.

현재 판매 중이고 재고가 있는 상품만 반환합니다. 이미 조회·구매한 상품은 제외하지 않습니다.
미등록 회원 ID는 인기 추천으로 처리하고, 비활성 회원은 오류로 거절합니다.
상품별 점수는 순위 계산용이며 구매 확률이 아닙니다.

이 실행은 현재 상품 스냅샷을 대상으로 한 추천 미리보기입니다.
과거 시점 Recall/NDCG 평가나 실시간 행동 수집, Java API 연결은 포함하지 않습니다.
현재 판매 상태를 그대로 사용해 과거 추천 성능을 평가하면 안 됩니다.
