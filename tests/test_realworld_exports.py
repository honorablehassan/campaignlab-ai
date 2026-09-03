import unittest
import numpy as np
import pandas as pd

from analytics.dataset_intelligence import analyze_dataset_intelligence
from analytics.marketing import analyze_marketing_efficiency
from analytics.cohorts import analyze_cohort_retention


class RealWorldExportTests(unittest.TestCase):
    def test_ga4_like_event_export_is_not_misread_as_aggregated_or_metric_time(self):
        rng=np.random.default_rng(44); n=5000
        df=pd.DataFrame({
            'event_date': rng.choice(pd.date_range('2026-01-01','2026-03-31'),n),
            'event_name': rng.choice(['page_view','add_to_cart','purchase'],n,p=[.8,.15,.05]),
            'user_pseudo_id':[f'u{x}' for x in rng.integers(0,1200,n)],
            'session_id':[f's{x}' for x in rng.integers(0,2200,n)],
            'source':rng.choice(['google','facebook','direct'],n),
            'medium':rng.choice(['cpc','paid_social','none'],n),
            'campaign':rng.choice(['brand','prospecting','direct'],n),
            'engagement_time_sec':rng.gamma(2,15,n),
            'is_conversion':rng.binomial(1,.05,n),
            'purchase_revenue':np.where(rng.random(n)<.05,rng.lognormal(4,.4,n),0),
        })
        intel=analyze_dataset_intelligence(df,'Which sources drive conversions and revenue?')
        self.assertEqual(intel.grain_guess,'likely event-level behavioral data')
        self.assertIn('event_date',intel.role_map['date'])
        self.assertNotIn('engagement_time_sec',intel.role_map['date'])
        self.assertIn('is_conversion',intel.role_map['binary_outcome'])
        self.assertNotIn('purchase_revenue',intel.role_map['binary_outcome'])
        self.assertIn('purchase_revenue',intel.role_map['revenue'])

    def test_meta_like_export_supports_efficiency_without_calling_value_binary(self):
        rng=np.random.default_rng(45); n=10000
        spend=rng.gamma(2,70,n); imp=np.maximum(100,(spend*50).astype(int)); clicks=rng.binomial(imp,.012); purchases=rng.binomial(clicks,.04)
        df=pd.DataFrame({
            'date':rng.choice(pd.date_range('2026-01-01','2026-06-30'),n),
            'platform':'Meta','campaign_name':rng.choice(['Prospecting','Retargeting','Brand'],n),
            'spend':spend,'impressions':imp,'clicks':clicks,'purchases':purchases,
            'purchase_value':purchases*rng.lognormal(4.1,.3,n),
        })
        intel=analyze_dataset_intelligence(df,'Which campaigns are efficient?')
        self.assertNotIn('purchase_value',intel.role_map['binary_outcome'])
        self.assertIn('purchase_value',intel.role_map['revenue'])
        result=analyze_marketing_efficiency(df,'campaign_name','spend','purchase_value','purchases','clicks','impressions')
        self.assertEqual(result['totals']['groups'],3)
        self.assertTrue(all(r['roas'] >= 0 for r in result['rows']))

    def test_ga4_like_repeated_user_events_support_cohort_engine(self):
        df=pd.DataFrame({
            'user_pseudo_id':['u1','u1','u1','u2','u2','u3'],
            'event_date':['2026-01-03','2026-02-01','2026-03-01','2026-01-15','2026-02-20','2026-02-10']
        })
        out=analyze_cohort_retention(df,'user_pseudo_id','event_date','M')
        self.assertGreaterEqual(len(out['cohorts']),2)
        self.assertEqual(out['frequency'],'M')

if __name__=='__main__': unittest.main()
