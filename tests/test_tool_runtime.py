import unittest
import pandas as pd

from analytics.tool_runtime import EvidenceToolRuntime
from core.errors import CampaignLabToolError


class ToolRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            "variant": ["control"] * 50 + ["treatment"] * 50,
            "converted": [0, 1] * 50,
            "ad_spend": range(100),
            "revenue": range(100, 200),
            "channel": ["search", "social"] * 50,
        })
        self.runtime = EvidenceToolRuntime(self.df)

    def test_raw_dataframe_is_not_returned_by_profile(self):
        result = self.runtime.execute("profile_dataset", {})
        self.assertIn("rows", result)
        self.assertNotIn("data", result)

    def test_binary_planner_contract(self):
        result=self.runtime.execute("plan_binary_ab", {"baseline_rate":0.05,"absolute_mde":0.005,"power":0.8,"alpha":0.05})
        self.assertGreater(result["sample_size_per_group"],1000)
        self.assertAlmostEqual(result["target_rate"],0.055)

    def test_unregistered_tool_rejected(self):
        with self.assertRaises(CampaignLabToolError):
            self.runtime.execute("run_arbitrary_python", {"code": "print(1)"})

    def test_method_ranking_is_structured(self):
        result = self.runtime.execute("rank_candidate_methods", {"question": "Did variant improve conversion?"})
        self.assertIn("ranked_methods", result)
        self.assertTrue(len(result["ranked_methods"]) > 0)


if __name__ == "__main__":
    unittest.main()
