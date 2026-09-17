import numpy as np
import pandas as pd
import pytest
from analytics.cuped import analyze_cuped

def _experiment(seed=91,n=3000):
    rng=np.random.default_rng(seed); group=np.where(np.arange(n)%2==0,"control","treatment"); rng.shuffle(group)
    pre=rng.normal(100,25,n); outcome=30+.8*pre+np.where(group=="treatment",5.0,0)+rng.normal(0,18,n)
    return pd.DataFrame({"group":group,"outcome":outcome,"pre":pre})

def test_cuped_recovers_effect_and_reduces_variance():
    result=analyze_cuped(_experiment(),"group","outcome","pre","control","treatment")
    assert 3<result["adjusted_effect"]<7
    assert result["adjusted_ci_low"]<result["adjusted_effect"]<result["adjusted_ci_high"]
    assert result["variance_reduction"]>.35
    assert abs(result["covariate_balance_smd"])<.1

def test_cuped_rejects_missing_constant_and_tiny_inputs():
    df=_experiment(n=30)
    with pytest.raises(ValueError): analyze_cuped(df,"group","outcome","missing","control","treatment")
    df["pre"]=1
    with pytest.raises(ValueError): analyze_cuped(df,"group","outcome","pre","control","treatment")

def test_cuped_flags_covariate_imbalance():
    df=_experiment(); df.loc[df["group"]=="treatment","pre"]+=20
    result=analyze_cuped(df,"group","outcome","pre","control","treatment")
    assert abs(result["covariate_balance_smd"])>.1
    assert any("imbalanced" in warning for warning in result["warnings"])
