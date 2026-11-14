"""로컬 Docker PostgreSQL 추천 목업. 실행: python scripts/seed_postgres.py

Python 패키지 설치 불필요. 기본 컨테이너 이름은 팀 compose의 psql.
각 PC에서 동일한 예시 데이터와 관계를 생성하며 PK는 각 DB가 발급한다.
"""

import argparse
import subprocess
import sys


from pathlib import Path

SQL = (Path(__file__).resolve().parents[1] / "docker/db/02-seed.sql").read_text(encoding="utf-8")


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
