"""End-to-end fixture checks, including deliberately corrupted datasets."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from generate_mock_data import generate, save
from validate_mock_data import validate


class MockDataTests(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parent
        self.tmp = tempfile.TemporaryDirectory(prefix="mock-test-", dir=test_root)
        self.assertTrue(Path(self.tmp.name).resolve().is_relative_to(test_root))
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.tables, self.meta = generate(7, 60, 10, 20)
        save(self.folder, self.tables, self.meta)

    def test_valid_relations_and_reproducibility(self):
        self.assertTrue(validate(self.folder)["valid"])
        other = self.folder / "again"
        save(other, *generate(7, 60, 10, 20))
        for path in self.folder.rglob("*.csv"):
            if other not in path.parents:
                self.assertEqual(path.read_bytes(), (other / path.relative_to(self.folder)).read_bytes())
        self.assertEqual((self.folder / "metadata.json").read_bytes(), (other / "metadata.json").read_bytes())

    def test_different_seed_and_larger_scale(self):
        save(self.folder, *generate(19, 120, 20, 30))
        report = validate(self.folder)
        self.assertEqual(report["products"], 120)
        self.assertEqual(report["users"], 20)

    def test_invalid_foreign_key_is_rejected(self):
        self.tables["interactions.csv"][0]["product_id"] = 999999
        save(self.folder, self.tables, self.meta)
        with self.assertRaisesRegex(ValueError, "Event user/product FK"):
            validate(self.folder)

    def test_cancelled_order_cannot_be_a_purchase(self):
        event = next(e for e in self.tables["interactions.csv"] if e["interaction_type"] == "purchase")
        order = next(o for o in self.tables["erd/orders.csv"] if o["order_id"] == event["order_id"])
        payment = next(p for p in self.tables["erd/payments.csv"] if p["order_id"] == order["order_id"])
        order["order_status"] = "CANCELLED"
        payment.update(status="CANCELED", canceled_at=payment["updated_at"], cancel_reason="test")
        save(self.folder, self.tables, self.meta)
        with self.assertRaisesRegex(ValueError, "Non-completed order treated as purchase"):
            validate(self.folder)

    def test_future_event_in_train_is_rejected(self):
        future = self.tables["splits/test.csv"].pop()
        self.tables["splits/train.csv"].append(future)
        save(self.folder, self.tables, self.meta)
        with self.assertRaisesRegex(ValueError, "Temporal split leakage"):
            validate(self.folder)

    def test_missing_header_is_rejected(self):
        target = self.folder / "users.csv"
        target.write_text("wrong_column\n1\n", encoding="utf-8-sig")
        with self.assertRaisesRegex(ValueError, "Columns: users.csv"):
            validate(self.folder)


if __name__ == "__main__":
    unittest.main()
