import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from analytics.mmm import hill_saturation, media_response, mmm_readiness, fit_mmm, optimize_budget

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
        self.assertEqual(out['method'],'marketing_mix_model_native_v2')
        self.assertEqual(set(out['channels']),set(self.media))
        self.assertLess(out['model']['holdout_wape'],.35)
        self.assertGreater(out['model']['uncertainty_samples'],0)
        self.assertTrue(out['model']['rolling_validation'])
        self.assertGreaterEqual(len(out['model']['expanding_window_backtests']),2)
        self.assertEqual(len(out['model']['control_sensitivity']),len(self.controls))
    def test_budget_optimizer_preserves_budget(self):
        out=fit_mmm(self.df,'week','revenue',self.media,self.controls)
        opt=optimize_budget(self.df,out,self.media)
        self.assertAlmostEqual(sum(opt['recommended'].values()),opt['total_weekly_budget'],places=2)
if __name__=='__main__': unittest.main()


def test_hill_saturation_is_monotone_bounded_and_hits_half_at_scale():
    import numpy as np
    values=np.asarray([0,25,50,100,1000],float)
    out=hill_saturation(values,50,1.5)
    assert np.all(np.diff(out)>=0)
    assert np.all((out>=0)&(out<=1))
    assert abs(out[2]-.5)<1e-12

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

    def test_experiment_calibration_moves_channel_toward_experimental_signal(self):
        base=fit_mmm(self._base(),'week','revenue',['a_spend','b_spend'],['promo','price'])
        channel='a_spend'; info=base['channels'][channel]
        baseline=100.0; treatment=125.0
        steady=np.asarray([baseline,treatment])/max(1-info['adstock_alpha'],1e-6)
        delta=float(np.diff(media_response(steady,info))[0])
        target_beta=max(info['coefficient']*1.5,.1)
        calibrated=fit_mmm(
            self._base(),'week','revenue',['a_spend','b_spend'],['promo','price'],
            experiment_calibrations=[{
                'channel':channel,'baseline_spend':baseline,'treatment_spend':treatment,
                'incremental_outcome':target_beta*delta,'standard_error':max(abs(target_beta*delta)*.1,.001),
            }],
        )
        detail=calibrated['model']['experiment_calibration'][0]
        self.assertGreater(detail['experiment_weight'],0)
        self.assertLessEqual(detail['experiment_weight'],1)
        self.assertLess(
            abs(detail['coefficient_after']-detail['experimental_coefficient']),
            abs(detail['model_coefficient_before']-detail['experimental_coefficient']),
        )

    def test_experiment_calibration_rejects_unknown_channel(self):
        with self.assertRaises(ValueError):
            fit_mmm(
                self._base(),'week','revenue',['a_spend','b_spend'],['promo','price'],
                experiment_calibrations=[{
                    'channel':'invented','baseline_spend':100,'treatment_spend':120,
                    'incremental_outcome':10,'standard_error':2,
                }],
            )
