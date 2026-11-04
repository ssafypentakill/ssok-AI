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

기본 추천 모델은 Hugging Face의 `intfloat/multilingual-e5-small`입니다.
프로젝트 가상환경에서 의존성을 설치하고 실행합니다.

```powershell
cd C:\Users\PC\Desktop\SOOKAI\ssok-AI
# .venv가 없다면 생성
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

모델을 웹사이트에서 수동으로 받을 필요는 없습니다. 첫 E5 실행 시 인터넷에 연결해
자동 다운로드합니다. 모델은 `.cache/recommendation/models/`, 상품 벡터는
`.cache/recommendation/vectors-*.json`에 저장되며 Git에서 제외됩니다.
같은 상품 ID·설명은 벡터 캐시를 재사용하므로 이후에는 모델을 로드하지 않습니다.
상품 설명이 바뀌면 내려받은 모델로 벡터를 다시 계산합니다.
모델은 CPU에서 실행하며, 외부 임베딩 API를 호출하거나 상품 설명을 업로드하지 않습니다.
첫 다운로드에는 시간과 디스크 공간이 필요합니다.

```powershell
# 비로그인: 인기 추천
.\.venv\Scripts\python.exe -m app.recommendation.recommender

# 행동이 없는 회원: 인기 추천
.\.venv\Scripts\python.exe -m app.recommendation.recommender --user-id 46 --limit 5

# 행동이 있는 회원: E5 AI 임베딩 개인화 + 인기 추천
.\.venv\Scripts\python.exe -m app.recommendation.recommender --user-id 1 --limit 5

# 기존 TF-IDF와 비교 (모델 다운로드 불필요)
.\.venv\Scripts\python.exe -m app.recommendation.recommender --backend tfidf --user-id 1 --limit 5

# 추천 기능 테스트만 실행
python -m unittest discover -s tests -p test_recommender.py -v

# 전체 테스트
python -m unittest discover -s tests -v
```

`Mode: popular`은 인기 추천, `Mode: personalized`는 개인화가 반영된 추천입니다.
`personalization`은 최종 점수에서 개인화 점수가 차지하는 비중입니다.

`app/recommendation/data_loader.py`가 기본적으로 train 데이터만 읽고,
`app/recommendation/embeddings.py`가 학습된 E5 모델로 상품 벡터를 생성합니다.
상품 간 유사도 비교이므로 공식 모델 안내에 따라 모든 설명 앞에 `query: `를 붙입니다.
`app/recommendation/recommender.py`가 상품 벡터와 행동 가중치
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

일반 테스트는 네트워크나 모델 다운로드 없이 TF-IDF 및 가짜 인코더로 로직을 검증합니다.
실제 E5 모델 통합 테스트는 다음과 같이 별도 실행합니다.

```powershell
$env:RUN_E5_INTEGRATION = "1"
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_embeddings.py -v
Remove-Item Env:RUN_E5_INTEGRATION
```

E5 벡터의 유사도 분포는 TF-IDF와 다르므로 기존 인기/개인화 혼합 비율은 초기값입니다.
모델 교체 후 실제 추천 품질과 비율은 validation으로 비교해야 합니다.
모델 설명과 MIT 라이선스: https://huggingface.co/intfloat/multilingual-e5-small

## JAVA - PYTHON DB  연동
Java 서버(Spring Boot)
    │
    │ HTTP 요청: “회원 1번(로그인)에게 추천할 상품 알려줘”
    ▼
Python 서버(FastAPI)
    │
    ├─ PostgreSQL에서 상품·사용자 행동 조회
    ├─ Python 추천 로직 실행
    │
    ▼
Java에 응답: 추천 상품 ID 목록


① 사용자가 쇼핑몰 메인 화면에 접속
                ↓
② 프론트엔드가 Java에 추천 상품 요청
                ↓
③ Java가 로그인 정보를 확인하고
   FastAPI에 해당 회원의 추천 요청
                ↓
④ FastAPI가 행동 이력으로 추천 계산
   → Java에 상품 ID 목록 반환
                ↓
⑤ Java가 상품명·가격·이미지와 판매 상태 확인
   → 프론트엔드에 상품 목록 반환
                ↓
⑥ 프론트엔드가 추천 상품 칸에 카드로 표시


