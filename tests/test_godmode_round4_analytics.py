import math
import numpy as np
import pandas as pd
import pytest

from analytics.ab_binary import analyze_binary_ab
from analytics.ab_continuous import analyze_continuous_ab
from analytics.regression import fit_linear_regression, fit_logistic_regression
from analytics.tree_models import fit_tree_model
from analytics.causal import run_difference_in_differences, run_interrupted_time_series
from analytics.marketing import analyze_marketing_efficiency
from analytics.data_gate import prediction_readiness, forecasting_readiness

# 60 binary A/B cases across base rates, effects, and sample sizes
AB_CASES=[]
for n in [100,500,2000,10000,100000]:
    for base in [.001,.01,.05,.2]:
        for lift in [0.0,.1,.5]:
            AB_CASES.append((n,base,lift))

@pytest.mark.parametrize('n,base,lift', AB_CASES)
def test_binary_ab_godmode_finite_and_bounded(n,base,lift):
    c=max(0,min(n,round(n*base)))
    t=max(0,min(n,round(n*base*(1+lift))))
    out=analyze_binary_ab(n,c,n,t)
    assert 0 <= out.p_value <= 1
    assert 0 <= out.fisher_p_value <= 1
    assert out.ci_low <= out.absolute_lift <= out.ci_high
    assert out.verdict in {'SHIP','HOLD',"DON'T SHIP"}
    assert out.srm_status=='pass'

# 30 continuous A/B cases
CONT_CASES=[]
for seed in range(10):
    for effect in [0.0,.25,1.0]: CONT_CASES.append((seed,effect))

@pytest.mark.parametrize('seed,effect', CONT_CASES)
def test_continuous_ab_godmode(seed,effect):
    rng=np.random.default_rng(seed)
    c=rng.normal(10,2,500)
    t=rng.normal(10+effect,2.5,530)
    out=analyze_continuous_ab(c,t)
    assert math.isfinite(out.absolute_lift)
    assert 0<=out.p_value<=1
    assert out.ci_low<=out.absolute_lift<=out.ci_high
    assert out.decision in {'SHIP','HOLD',"DON'T SHIP"}

# 20 known-truth DiD cases
@pytest.mark.parametrize('seed', list(range(20)))
def test_did_recovers_known_effect(seed):
    rng=np.random.default_rng(seed)
    units=100; periods=8
    rows=[]; true=5.0
    for u in range(units):
        treated=int(u>=units//2)
        unit_fe=rng.normal(0,2)
        for p in range(periods):
            post=int(p>=4)
            y=20+unit_fe+1.2*p+2*treated+true*treated*post+rng.normal(0,1.5)
            rows.append((u,treated,post,y))
    df=pd.DataFrame(rows,columns=['unit','treated','post','y'])
    out=run_difference_in_differences(df,'y','treated','post',unit_col='unit')
    assert abs(out['effect']-true)<1.0
    assert out['ci_low'] < out['effect'] < out['ci_high']

# 10 null DiD cases should stay near zero
@pytest.mark.parametrize('seed', list(range(10)))
def test_did_null_does_not_invent_large_effect(seed):
    rng=np.random.default_rng(seed)
    rows=[]
    for u in range(80):
        treated=int(u>=40)
        for p in range(8):
            post=int(p>=4)
            y=50+1.5*p+3*treated+rng.normal(0,2)
            rows.append((u,treated,post,y))
    df=pd.DataFrame(rows,columns=['unit','treated','post','y'])
    out=run_difference_in_differences(df,'y','treated','post',unit_col='unit')
    assert abs(out['effect'])<1.5

# 12 ITS known level shifts
@pytest.mark.parametrize('seed', list(range(12)))
def test_its_recovers_level_shift(seed):
    rng=np.random.default_rng(seed)
    n=80; intervention=40; true=8.0
    t=np.arange(n)
    y=100+.5*t+(t>=intervention)*true+rng.normal(0,1.5,n)
    df=pd.DataFrame({'date':pd.date_range('2024-01-01',periods=n,freq='W'),'y':y})
    out=run_interrupted_time_series(df,'y','date',str(df.loc[intervention,'date'].date()))
    assert abs(out['level_change']-true)<2.5
    assert math.isfinite(out['r2'])

# 20 linear regression known coefficient cases
@pytest.mark.parametrize('seed', list(range(20)))
def test_linear_regression_recovers_signal(seed):
    rng=np.random.default_rng(seed); n=1000
    x1=rng.normal(size=n); x2=rng.normal(size=n)
    y=4+2.5*x1-1.2*x2+rng.normal(0,.5,n)
    df=pd.DataFrame({'y':y,'x1':x1,'x2':x2})
    out=fit_linear_regression(df,'y',['x1','x2'])
    coef={r['term']:r['coefficient'] for r in out['coefficients']}
    assert abs(coef['x1']-2.5)<.15
    assert abs(coef['x2']+1.2)<.15
    assert out['r2']>.9

# 10 logistic regression valid signal
@pytest.mark.parametrize('seed', list(range(10)))
def test_logistic_regression_signal(seed):
    rng=np.random.default_rng(seed); n=2000
    x=rng.normal(size=n); z=rng.normal(size=n)
    p=1/(1+np.exp(-(-.5+1.2*x-.7*z)))
    y=rng.binomial(1,p)
    df=pd.DataFrame({'y':y,'x':x,'z':z})
    out=fit_logistic_regression(df,'y',['x','z'])
    assert out['auc_in_sample']>.7
    assert 0<=out['brier_in_sample']<=1

# 12 tree model cases: meaningful vs noise
@pytest.mark.parametrize('seed', list(range(6)))
def test_tree_model_signal_auc(seed):
    rng=np.random.default_rng(seed); n=3000
    x=rng.normal(size=n); z=rng.normal(size=n)
    y=(x+0.5*z+rng.normal(0,.7,n)>0).astype(int)
    df=pd.DataFrame({'y':y,'x':x,'z':z})
    out=fit_tree_model(df,'y',['x','z'],task='classification')
    assert out['metrics']['auc_holdout']>.75

@pytest.mark.parametrize('seed', list(range(6)))
def test_tree_model_noise_does_not_look_magically_great(seed):
    rng=np.random.default_rng(seed); n=3000
    x=rng.normal(size=n); z=rng.normal(size=n); y=rng.binomial(1,.5,n)
    df=pd.DataFrame({'y':y,'x':x,'z':z})
    out=fit_tree_model(df,'y',['x','z'],task='classification')
    assert out['metrics']['auc_holdout']<.62

# 15 prediction readiness cases
@pytest.mark.parametrize('rows,preds,expected_not_blocked', [
    (30,2,False),(49,2,False),(50,2,False),(79,2,True),(100,2,True),
    (200,1,True),(200,2,True),(200,5,True),(200,10,True),(200,20,False),
    (1000,5,True),(1000,20,True),(1000,40,True),(5000,40,True),(10000,100,True),
])
def test_prediction_readiness_complexity(rows,preds,expected_not_blocked):
    rng=np.random.default_rng(rows+preds)
    data={f'x{i}':rng.normal(size=rows) for i in range(preds)}
    data['y']=rng.binomial(1,.3,rows)
    df=pd.DataFrame(data)
    out=prediction_readiness(df,'y',[f'x{i}' for i in range(preds)])
    assert (out.status!='blocked') is expected_not_blocked

# 12 forecasting readiness cases
@pytest.mark.parametrize('n,horizon,seasonal', [
    (12,4,12),(24,4,12),(36,4,12),(52,4,12),(104,8,52),(156,12,52),
    (30,20,12),(60,20,12),(120,20,12),(365,30,7),(730,60,7),(1000,90,7),
])
def test_forecasting_readiness_varied_history(n,horizon,seasonal):
    df=pd.DataFrame({'date':pd.date_range('2024-01-01',periods=n,freq='D'),'y':np.arange(n)+np.random.default_rng(n).normal(size=n)})
    out=forecasting_readiness(df,'date','y',seasonal_period=seasonal,horizon=horizon)
    assert 0<=out.score<=100
    assert out.status in {'ready','caution','blocked'}

# 16 marketing efficiency invariants
@pytest.mark.parametrize('groups', [2,3,5,10])
@pytest.mark.parametrize('scale', [1,10,100,1000])
def test_marketing_efficiency_totals_and_ratios(groups,scale):
    rows=[]
    for g in range(groups):
        rows.append((f'g{g}',100*scale*(g+1),250*scale*(g+1),1000*(g+1),50*(g+1),5*(g+1)))
    df=pd.DataFrame(rows,columns=['channel','spend','revenue','impressions','clicks','conversions'])
    out=analyze_marketing_efficiency(df,'channel','spend','revenue','conversions','clicks','impressions')
    assert out['totals']['groups']==groups
    assert out['totals']['spend']==pytest.approx(df['spend'].sum())
    for r in out['rows']:
        assert r['roas']==pytest.approx(2.5)
        assert r['ctr']==pytest.approx(.05)
        assert r['cvr']==pytest.approx(.1)
