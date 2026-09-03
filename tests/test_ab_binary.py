import unittest

from analytics.ab_binary import analyze_binary_ab, required_sample_size_per_group


class BinaryABTests(unittest.TestCase):
    def test_sample_size_increases_for_smaller_mde(self):
        n_big = required_sample_size_per_group(0.05, 0.06, power=0.8)
        n_small = required_sample_size_per_group(0.05, 0.055, power=0.8)
        self.assertGreater(n_small, n_big)

    def test_invalid_conversion_count_rejected(self):
        with self.assertRaises(ValueError):
            analyze_binary_ab(100, 101, 100, 10)

    def test_clear_positive_effect_ships_when_threshold_cleared(self):
        result = analyze_binary_ab(
            control_n=50000, control_conversions=2500,
            treatment_n=50000, treatment_conversions=3100,
            business_threshold=0.002,
        )
        self.assertGreater(result.absolute_lift, 0)
        self.assertEqual(result.srm_status, "pass")
        self.assertEqual(result.verdict, "SHIP")
        self.assertGreater(result.ci_low, 0.002)

    def test_srm_blocks_action(self):
        result = analyze_binary_ab(
            control_n=9000, control_conversions=450,
            treatment_n=11000, treatment_conversions=650,
            expected_treatment_share=0.5,
        )
        self.assertEqual(result.srm_status, "fail")
        self.assertEqual(result.verdict, "HOLD")

    def test_nullish_result_holds(self):
        result = analyze_binary_ab(10000, 500, 10000, 505, business_threshold=0.0025)
        self.assertEqual(result.verdict, "HOLD")


if __name__ == "__main__":
    unittest.main()
