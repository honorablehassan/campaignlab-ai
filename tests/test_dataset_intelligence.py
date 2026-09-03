import unittest
import pandas as pd

from analytics.dataset_intelligence import analyze_dataset_intelligence


class DatasetIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            "user_id": [f"u{i}" for i in range(200)],
            "variant": ["control"] * 100 + ["treatment"] * 100,
            "converted": [0, 1] * 100,
            "channel": ["search", "social", "email", "search"] * 50,
            "ad_spend": [10.0 + i / 100 for i in range(200)],
            "revenue": [20.0 + i / 10 for i in range(200)],
            "event_date": pd.date_range("2026-01-01", periods=200, freq="D"),
        })

    def test_roles_are_detected(self):
        intel = analyze_dataset_intelligence(self.df, "Did the treatment improve conversion?")
        self.assertIn("variant", intel.role_map["treatment"])
        self.assertIn("converted", intel.role_map["binary_outcome"])
        self.assertIn("ad_spend", intel.role_map["spend"])
        self.assertIn("revenue", intel.role_map["revenue"])
        self.assertIn("event_date", intel.role_map["date"])

    def test_numeric_measures_are_not_ids_just_because_unique(self):
        intel = analyze_dataset_intelligence(self.df, "")
        self.assertNotIn("revenue", intel.role_map["id"])
        self.assertNotIn("ad_spend", intel.role_map["id"])

    def test_causal_question_without_treatment_is_blocked(self):
        df = self.df.drop(columns=["variant"])
        intel = analyze_dataset_intelligence(df, "What caused conversion lift?")
        self.assertEqual(intel.question_assessment["status"], "blocked")

    def test_roas_question_requires_spend_and_revenue(self):
        df = self.df.drop(columns=["ad_spend"])
        intel = analyze_dataset_intelligence(df, "Which channel has the best ROAS?")
        self.assertEqual(intel.question_assessment["status"], "blocked")
        self.assertTrue(any("spend" in x.lower() for x in intel.question_assessment["blockers"]))


if __name__ == "__main__":
    unittest.main()
