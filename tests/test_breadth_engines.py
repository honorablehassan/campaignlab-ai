import unittest
import numpy as np
import pandas as pd

from analytics.ab_continuous import analyze_continuous_ab
from analytics.abn import analyze_abn
from analytics.bootstrap import bootstrap_group_difference
from analytics.causal import run_difference_in_differences, run_event_study, run_interrupted_time_series
from analytics.cohorts import analyze_cohort_retention
from analytics.marketing import analyze_marketing_efficiency, analyze_funnel
from analytics.regression import fit_linear_regression, fit_logistic_regression
from analytics.tree_models import fit_tree_model
from analytics.unsupervised import segment_kmeans, detect_anomalies


class BreadthEngineTests(unittest.TestCase):
    def setUp(self):
        self.rng=np.random.default_rng(123)

    def test_continuous_ab_detects_positive_effect(self):
        c=self.rng.normal(0,1,800); t=self.rng.normal(.5,1,800)
        r=analyze_continuous_ab(c,t)
        self.assertGreater(r.absolute_lift,.35); self.assertLess(r.p_value,.001)

    def test_continuous_ab_rejects_tiny_groups(self):
        with self.assertRaises(ValueError): analyze_continuous_ab([1],[2,3])

    def test_abn_binary_holm(self):
        df=pd.DataFrame({'arm':np.repeat(['A','B','C'],800),'y':np.r_[self.rng.binomial(1,.08,800),self.rng.binomial(1,.11,800),self.rng.binomial(1,.16,800)]})
        r=analyze_abn(df,'arm','y','binary','A')
        self.assertEqual(len(r['arms']),3); self.assertEqual(r['multiple_testing'],'Holm family-wise error correction')

    def test_abn_requires_three_arms(self):
        df=pd.DataFrame({'arm':['A']*20+['B']*20,'y':[0,1]*20})
        with self.assertRaises(ValueError): analyze_abn(df,'arm','y','binary','A')

    def test_linear_regression_recovers_signal(self):
        n=600; x=self.rng.normal(size=n); z=self.rng.normal(size=n); y=1+2*x-.5*z+self.rng.normal(scale=.5,size=n)
        r=fit_linear_regression(pd.DataFrame({'y':y,'x':x,'z':z}),'y',['x','z'])
        coef={x['term']:x['coefficient'] for x in r['coefficients']}
        self.assertAlmostEqual(coef['x'],2,delta=.15); self.assertGreater(r['r2'],.8)

    def test_logistic_regression_has_discrimination(self):
        n=900; x=self.rng.normal(size=n); p=1/(1+np.exp(-1.5*x)); y=self.rng.binomial(1,p)
        r=fit_logistic_regression(pd.DataFrame({'y':y,'x':x}),'y',['x'])
        self.assertGreater(r['auc_in_sample'],.75)

    def test_tree_model_uses_holdout(self):
        n=700; x=self.rng.normal(size=n); y=(x+self.rng.normal(scale=.5,size=n)>0).astype(int)
        r=fit_tree_model(pd.DataFrame({'y':y,'x':x}),'y',['x'],'classification','random_forest')
        self.assertIn('auc_holdout',r['metrics']); self.assertGreater(r['metrics']['auc_holdout'],.8)

    def test_marketing_efficiency_roas(self):
        df=pd.DataFrame({'channel':['A','A','B'],'spend':[100,100,100],'revenue':[300,300,100],'conv':[10,10,5]})
        r=analyze_marketing_efficiency(df,'channel','spend','revenue','conv')
        a=next(x for x in r['rows'] if x['group']=='A'); self.assertAlmostEqual(a['roas'],3)

    def test_funnel_rates(self):
        df=pd.DataFrame({'imp':[1000],'click':[100],'conv':[10]})
        r=analyze_funnel(df,['imp','click','conv'])
        self.assertAlmostEqual(r['stages'][2]['from_start'],.01)

    def test_cohort_retention(self):
        df=pd.DataFrame({'customer_id':[1,1,1,2,2],'date':pd.to_datetime(['2026-01-01','2026-02-01','2026-03-01','2026-01-05','2026-02-05'])})
        r=analyze_cohort_retention(df,'customer_id','date','M')
        self.assertEqual(r['cohorts'][0]['size'],2); self.assertAlmostEqual(r['cohorts'][0]['retention_by_age']['1'],1.0)

    def test_did_recovers_interaction(self):
        rows=[]
        for u in range(80):
            tr=u>=40
            for post in [0,1]:
                for _ in range(4): rows.append((u,int(tr),post,5+.4*post+(1.8 if tr and post else 0)+self.rng.normal(0,.4)))
        df=pd.DataFrame(rows,columns=['unit','tr','post','y'])
        r=run_difference_in_differences(df,'y','tr','post',[], 'unit')
        self.assertAlmostEqual(r['effect'],1.8,delta=.25)

    def test_event_study_returns_dynamic_effects(self):
        rows=[]
        for u in range(16):
            tr=u>=8
            for rel in range(-3,4):
                eff=(1.0*max(rel,0)) if tr else 0
                rows.append((u,int(tr),rel,rel+10,4+.1*rel+eff+self.rng.normal(0,.15)))
        df=pd.DataFrame(rows,columns=['unit','tr','rel','cal','y'])
        r=run_event_study(df,'y','tr','rel','unit','cal',-1,[])
        self.assertTrue(any(e['relative_time']==3 for e in r['effects']))
        post3=next(e for e in r['effects'] if e['relative_time']==3); self.assertGreater(post3['effect'],2.4)

    def test_interrupted_time_series_level_change(self):
        n=80; dates=pd.date_range('2025-01-01',periods=n,freq='D'); t=np.arange(n); y=2+.03*t+2*(t>=40)+self.rng.normal(0,.1,n)
        r=run_interrupted_time_series(pd.DataFrame({'date':dates,'y':y}),'y','date',str(dates[40].date()))
        self.assertAlmostEqual(r['level_change'],2,delta=.3)

    def test_bootstrap_effect(self):
        df=pd.DataFrame({'g':['c']*200+['t']*200,'y':np.r_[self.rng.normal(0,1,200),self.rng.normal(.7,1,200)]})
        r=bootstrap_group_difference(df,'g','y','c','t','mean',1000,1)
        self.assertGreater(r['effect'],.4); self.assertGreater(r['ci_low'],0)

    def test_kmeans_segmentation(self):
        a=self.rng.normal(loc=[-2,-2],scale=.3,size=(80,2)); b=self.rng.normal(loc=[2,2],scale=.3,size=(80,2)); X=np.vstack([a,b])
        r=segment_kmeans(pd.DataFrame(X,columns=['x','z']),['x','z'],2)
        self.assertEqual(r['k'],2); self.assertGreater(r['silhouette'],.7)

    def test_anomaly_detection(self):
        x=self.rng.normal(size=(200,2)); x[0]=[9,9]
        r=detect_anomalies(pd.DataFrame(x,columns=['x','z']),['x','z'],.02)
        self.assertTrue(any(a['row_index']=='0' for a in r['top_anomalies'][:5]))


if __name__=='__main__': unittest.main()
