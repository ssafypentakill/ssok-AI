from fastapi import FastAPI, Query

from app.recommendation.service import recommend_for_member

app = FastAPI(title="SSOK 추천 API")

@app.get("/recommendations")
def get_recommendations(
    member_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=10, ge=1, le=50),
):
    return recommend_for_member(member_id=member_id, limit=limit)