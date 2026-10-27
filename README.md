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
