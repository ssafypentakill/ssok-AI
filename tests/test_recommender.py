"""Behavior checks with a tiny, deliberately controlled catalog."""
"""
python -m app.recommendation.recommender --user-id 46 --limit 5
user id 46번에게 추천할 상품 5개 반환 
이때 user는 user.csv에 있음
행동 없을때 -> 인기 상품 추천
행동 있을때 -> 그 행동을 기반으로 추천함
"""
import unittest

from app.recommendation.data_loader import RecommendationData, load_recommendation_data
from app.recommendation.recommender import Recommender


def product(pid, text, active=True, stock=10):
    return {"product_id": pid, "name": text, "embedding_text": text,
            "is_active": active, "stock": stock}


def event(uid, pid, action):
    return {"user_id": uid, "product_id": pid, "interaction_type": action}


class RecommenderTests(unittest.TestCase):
    def setUp(self):
        self.data = RecommendationData(
            products={
                1: product(1, "오디오 무선 이어폰"),
                2: product(2, "오디오 무선 헤드폰"),
                3: product(3, "주방 요리 냄비"),
                4: product(4, "오디오 무선", stock=0),
                5: product(5, "오디오 무선", active=False),
            },
            users={uid: {"status": "active"} for uid in (1, 2, 3)},
            interactions=[event(1, 1, "purchase"), event(2, 3, "purchase"),
                          event(2, 3, "cart")],
        )
        self.data.users[4] = {"status": "inactive"}
        self.model = Recommender(self.data, backend="tfidf")

    def test_anonymous_and_new_user_receive_same_popular_results(self):
        anonymous = self.model.recommend()
        self.assertEqual(anonymous["mode"], "popular")
        self.assertEqual(anonymous["items"][0]["product_id"], 3)
        self.assertEqual(anonymous, self.model.recommend(3))
        self.assertEqual(anonymous, self.model.recommend(999))

    def test_behavior_promotes_similar_unseen_product(self):
        result = self.model.recommend(1)
        self.assertEqual(result["mode"], "personalized")
        ids = [item["product_id"] for item in result["items"]]
        self.assertLess(ids.index(2), ids.index(3))
        # Product 2 has no behavior but is still discoverable via its text.
        self.assertEqual(self.model.popularity[2], 0)

    def test_less_evidence_means_less_personalization(self):
        strong = self.model.recommend(1)["personalization_weight"]
        self.data.interactions = [event(1, 1, "view")]
        weak = Recommender(self.data, backend="tfidf").recommend(1)["personalization_weight"]
        self.assertGreater(weak, 0)
        self.assertLess(weak, strong)

    def test_unavailable_products_never_appear(self):
        for uid in (None, 1):
            ids = {item["product_id"] for item in self.model.recommend(uid)["items"]}
            self.assertTrue(ids.isdisjoint({4, 5}))

    def test_inactive_user_and_invalid_limit_rejected(self):
        with self.assertRaisesRegex(ValueError, "Inactive"):
            self.model.recommend(4)
        with self.assertRaises(ValueError):
            self.model.recommend(limit=0)

    def test_empty_history_and_catalog(self):
        self.data.interactions = []
        model = Recommender(self.data, backend="tfidf")
        self.assertEqual(model.recommend(1)["mode"], "popular")
        self.assertEqual(model.recommend(), model.recommend())
        self.data.products = {}
        self.assertEqual(Recommender(self.data, backend="tfidf").recommend()["items"], [])

    def test_real_mock_data_default_and_personalized(self):
        data = load_recommendation_data()
        self.assertEqual(len(data.interactions), 7312)
        model = Recommender(data, backend="tfidf")
        self.assertEqual(model.recommend(46)["mode"], "popular")
        self.assertEqual(model.recommend(1)["mode"], "personalized")
        self.assertEqual(len(model.recommend(1)["items"]), 10)


if __name__ == "__main__":
    unittest.main()
