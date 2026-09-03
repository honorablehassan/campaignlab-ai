import unittest
from analytics.method_registry import METHODS, live_methods
from analytics.tool_runtime import EvidenceToolRuntime

class RegistryBreadthTests(unittest.TestCase):
    def test_live_methods_have_documentation_contract(self):
        required={'id','family','name','status','answers','requires','use_cases','assumptions','diagnostics','outputs','visuals','caution'}
        for m in live_methods(): self.assertTrue(required.issubset(m),m['id'])

    def test_expected_live_breadth(self):
        ids={m['id'] for m in live_methods()}
        expected={'binary_ab','continuous_ab','abn','bootstrap_difference','linear_regression','logistic_regression','tree_model','marketing_efficiency','funnel','cohort_retention','did','event_study','interrupted_time_series','kmeans_segmentation','anomaly_detection'}
        self.assertTrue(expected.issubset(ids))

    def test_no_duplicate_method_ids(self):
        ids=[m['id'] for m in METHODS]; self.assertEqual(len(ids),len(set(ids)))

    def test_tool_specs_include_breadth_when_dataset_loaded(self):
        import pandas as pd
        rt=EvidenceToolRuntime(pd.DataFrame({'x':[1,2,3]})); names={x['name'] for x in rt.tool_specs()}
        for n in ['fit_linear_regression','fit_logistic_regression','fit_tree_model','run_difference_in_differences','run_event_study','analyze_marketing_efficiency']:
            self.assertIn(n,names)

if __name__=='__main__': unittest.main()
