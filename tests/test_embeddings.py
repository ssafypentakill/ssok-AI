"""Offline unit tests plus an opt-in real E5 integration test."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.recommendation.embeddings import e5_vectors
from app.recommendation.data_loader import load_recommendation_data
from app.recommendation.recommender import Recommender


class EmbeddingTests(unittest.TestCase):
    def test_prefix_product_order_cache_and_text_change(self):
        encoder = Mock()
        encoder.encode.return_value.tolist.return_value = [[1.0] + [0.0] * 383] * 2
        factory = Mock(return_value=encoder)
        products = {2: {"embedding_text": "헤드폰"}, 1: {"embedding_text": "이어폰"}}
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            with patch.dict(sys.modules, {"sentence_transformers": SimpleNamespace(SentenceTransformer=factory)}):
                first = e5_vectors(products, Path(folder))
                self.assertEqual(list(first), [1, 2])
                self.assertEqual(encoder.encode.call_args.args[0], ["query: 이어폰", "query: 헤드폰"])
                self.assertTrue(encoder.encode.call_args.kwargs["normalize_embeddings"])
                self.assertEqual(first, e5_vectors(products, Path(folder)))
                self.assertEqual(factory.call_count, 1)
                products[1]["embedding_text"] = "새 이어폰"
                e5_vectors(products, Path(folder))
                self.assertEqual(factory.call_count, 2)

    def test_e5_vectors_drive_personalization(self):
        data = load_recommendation_data()
        vectors = {pid: {0: 1.0, 1: 0.0} for pid in data.products}
        with patch("app.recommendation.recommender.e5_vectors", return_value=vectors) as encode:
            model = Recommender(data)
            encode.assert_called_once_with(data.products)
            self.assertEqual(model.recommend(1)["mode"], "personalized")
            self.assertEqual(model.recommend(46)["mode"], "popular")

    @unittest.skipUnless(os.environ.get("RUN_E5_INTEGRATION") == "1", "Set RUN_E5_INTEGRATION=1 to run the real model")
    def test_real_e5_model(self):
        data = load_recommendation_data()
        model = Recommender(data)
        self.assertEqual(len(model.vectors), len(data.products))
        self.assertEqual(len(next(iter(model.vectors.values()))), 384)
        self.assertEqual(model.recommend(46)["mode"], "popular")
        result = model.recommend(1)
        self.assertEqual(result["mode"], "personalized")
        self.assertEqual(len(result["items"]), 10)
        for item in result["items"]:
            product = data.products[item["product_id"]]
            self.assertTrue(product["is_active"] and product["stock"] > 0)


if __name__ == "__main__":
    unittest.main()
