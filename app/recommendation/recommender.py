"""Popularity blended with E5 or TF-IDF personalization."""

import argparse
import math
import re
from collections import Counter, defaultdict

from app.recommendation.data_loader import RecommendationData, load_recommendation_data
from app.recommendation.embeddings import e5_vectors


WEIGHTS = {"view": 1, "like": 3, "cart": 5, "purchase": 10}


def _normalize(vector):
    length = math.sqrt(sum(value * value for value in vector.values()))
    return {key: value / length for key, value in vector.items()} if length else {}


class Recommender:
    """Fit using training events only; availability is the current snapshot.

    Each event counts once regardless of quantity. Repeated user/product/action
    signals are capped at three to limit repeated-view dominance. Seen products
    remain eligible; this version does not impose a repurchase exclusion policy.
    """

    def __init__(self, data: RecommendationData, *, backend: str = "e5"):
        if backend not in {"e5", "tfidf"}:
            raise ValueError("backend must be e5 or tfidf")
        self.data = data
        self.backend = backend
        self.vectors = (
            e5_vectors(data.products) if backend == "e5" else self._tfidf_vectors(data.products)
        )
        self.popularity = Counter()
        self.history = defaultdict(Counter)
        counts = Counter(
            (event["user_id"], event["product_id"], event["interaction_type"])
            for event in data.interactions
        )
        for (uid, pid, action), count in counts.items():
            weight = WEIGHTS[action] * min(count, 3)
            self.popularity[pid] += weight
            self.history[uid][pid] += weight

    @staticmethod
    def _tfidf_vectors(products):
        terms = {
            pid: Counter(re.findall(r"\w+", product["embedding_text"].lower()))
            for pid, product in products.items()
        }
        frequency = Counter(token for counts in terms.values() for token in counts)
        total = len(terms)
        return {
            pid: _normalize({
                token: (1 + math.log(count)) * (1 + math.log((1 + total) / (1 + frequency[token])))
                for token, count in counts.items()
            })
            for pid, counts in terms.items()
        }

    def recommend(self, user_id: int | None = None, limit: int = 10) -> dict:
        """Anonymous/unknown users get popularity; inactive members are rejected."""
        if limit <= 0:
            raise ValueError("limit must be positive")
        user = self.data.users.get(user_id)
        if user is not None and user["status"] != "active":
            raise ValueError("Inactive users cannot request recommendations")
        history = self.history.get(user_id, {}) if user is not None else {}
        profile = defaultdict(float)
        for pid, weight in history.items():
            for token, value in self.vectors[pid].items():
                profile[token] += weight * value
        profile = _normalize(profile)
        # One view gives 10% personalization; sufficient evidence gives up to 80%.
        alpha = min(0.8, sum(history.values()) / 10) if profile else 0.0
        candidates = [
            product for product in self.data.products.values()
            if product["is_active"] and product["stock"] > 0
        ]
        max_popularity = max((self.popularity[p["product_id"]] for p in candidates), default=0)
        items = []
        for product in candidates:
            pid = product["product_id"]
            popular = self.popularity[pid] / max_popularity if max_popularity else 0.0
            similarity = sum(value * self.vectors[pid].get(token, 0) for token, value in profile.items())
            items.append({
                "product_id": pid, "name": product["name"],
                "score": alpha * similarity + (1 - alpha) * popular,
                "similarity": similarity, "popularity_score": popular,
            })
        items.sort(key=lambda item: (-item["score"], item["product_id"]))
        return {
            "mode": "personalized" if alpha else "popular",
            "personalization_weight": alpha,
            "items": items[:limit],
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preview current recommendations using train events only")
    parser.add_argument("--user-id", type=int, default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--backend", choices=("e5", "tfidf"), default="e5")
    args = parser.parse_args()
    result = Recommender(load_recommendation_data(), backend=args.backend).recommend(args.user_id, args.limit)
    print(f"Backend: {args.backend}")
    print(f"Mode: {result['mode']}; personalization: {result['personalization_weight']:.0%}")
    for rank, item in enumerate(result["items"], 1):
        print(f"{rank:2}. [{item['product_id']}] {item['name']} (score={item['score']:.4f})")
