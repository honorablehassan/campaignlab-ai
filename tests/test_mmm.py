import unittest
from pathlib import Path
import pandas as pd
from analytics.mmm import mmm_readiness, fit_mmm, optimize_budget

class MMMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df=pd.read_csv(Path(__file__).resolve().parents[1]/'examples'/'demo_mmm_weekly.csv')
        cls.media=['meta_spend','paid_search_spend','youtube_spend','tv_spend']
        cls.controls=['promotion','holiday_period','price_index']
    def test_demo_is_mmm_usable(self):
        r=mmm_readiness(self.df,'week','revenue',self.media,self.controls)
        self.assertNotEqual(r.report.status,'blocked')
        self.assertGreaterEqual(r.report.score,60)
    def test_beta_mmm_runs_and_returns_channels(self):
        out=fit_mmm(self.df,'week','revenue',self.media,self.controls)
        self.assertEqual(out['status'],'Beta')
        self.assertEqual(set(out['channels']),set(self.media))
        self.assertLess(out['model']['holdout_wape'],.35)
    def test_budget_optimizer_preserves_budget(self):
        out=fit_mmm(self.df,'week','revenue',self.media,self.controls)
        opt=optimize_budget(self.df,out,self.media)
        self.assertAlmostEqual(sum(opt['recommended'].values()),opt['total_weekly_budget'],places=2)
if __name__=='__main__': unittest.main()

class MMMRedTeamTests(unittest.TestCase):
    def setUp(self):
        import numpy as np
        self.n=156
        self.rng=np.random.default_rng(707)
        self.dates=pd.date_range('2023-01-01',periods=self.n,freq='W')

    def _base(self):
        import numpy as np
        return pd.DataFrame({
            'week':self.dates,
            'revenue':1000+self.rng.normal(0,20,self.n),
            'a_spend':100+self.rng.normal(0,15,self.n),
            'b_spend':80+self.rng.normal(0,12,self.n),
            'promo':self.rng.binomial(1,.1,self.n),
            'price':1+self.rng.normal(0,.02,self.n),
        })

    def test_constant_outcome_is_blocked(self):
        df=self._base(); df['revenue']=1000
        r=mmm_readiness(df,'week','revenue',['a_spend','b_spend'],['promo','price'])
        self.assertEqual(r.report.status,'blocked')

    def test_negative_media_is_blocked(self):
        df=self._base(); df.loc[:10,'a_spend']=-100
        r=mmm_readiness(df,'week','revenue',['a_spend','b_spend'],['promo','price'])
        self.assertEqual(r.report.status,'blocked')

    def test_duplicate_periods_are_blocked(self):
        df=self._base(); df=pd.concat([df,df.iloc[:5]],ignore_index=True)
        r=mmm_readiness(df,'week','revenue',['a_spend','b_spend'],['promo','price'])
        self.assertEqual(r.report.status,'blocked')

    def test_no_media_signal_downgrades_evidence(self):
        import numpy as np
        t=np.arange(self.n)
        a=100+30*np.sin(t*2*np.pi/52)+self.rng.normal(0,5,self.n)
        b=80+20*np.cos(t*2*np.pi/52)+self.rng.normal(0,5,self.n)
        y=1000+200*np.sin(t*2*np.pi/52)+self.rng.normal(0,25,self.n)
        df=pd.DataFrame({'week':self.dates,'revenue':y,'a_spend':a,'b_spend':b,'promo':self.rng.binomial(1,.1,self.n),'price':1+self.rng.normal(0,.01,self.n)})
        out=fit_mmm(df,'week','revenue',['a_spend','b_spend'],['promo','price'])
        self.assertEqual(out['model']['evidence_strength'],'Limited')

    def test_optimizer_refuses_extreme_extrapolation(self):
        df=self._base()
        out=fit_mmm(df,'week','revenue',['a_spend','b_spend'],['promo','price'])
        with self.assertRaises(ValueError):
            optimize_budget(df,out,['a_spend','b_spend'],1_000_000_000)
