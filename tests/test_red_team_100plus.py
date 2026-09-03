import math
import numpy as np
import pandas as pd
import pytest

from analytics.dataset_intelligence import analyze_dataset_intelligence
from analytics.mmm import mmm_readiness, fit_mmm, optimize_budget, geometric_adstock, saturation
from analytics.ab_binary import analyze_binary_ab, required_sample_size_per_group, wilson_interval
from analytics.ab_continuous import analyze_continuous_ab
from analytics.abn import analyze_abn
from analytics.bootstrap import bootstrap_group_difference
from analytics.marketing import analyze_marketing_efficiency, analyze_funnel
from analytics.regression import fit_linear_regression, fit_logistic_regression
from analytics.tree_models import fit_tree_model
from analytics.causal import run_difference_in_differences, run_interrupted_time_series

# ---------------- Dataset Intelligence: naming + semantic traps ----------------
ROLE_CASES = [
    ("event_date", pd.date_range("2026-01-01", periods=40), "date", True),
    ("created_at", pd.date_range("2026-01-01", periods=40), "date", True),
    ("week", pd.date_range("2026-01-04", periods=40, freq="W"), "date", True),
    ("engagement_time_sec", np.arange(40), "date", False),
    ("time_on_page", np.arange(40), "date", False),
    ("delivery_time_ms", np.arange(40), "date", False),
    ("purchase_revenue", np.arange(40, dtype=float), "revenue", True),
    ("purchase_revenue", np.arange(40, dtype=float), "binary_outcome", False),
    ("purchase_value", np.arange(40, dtype=float), "revenue", True),
    ("purchase_value", np.arange(40, dtype=float), "binary_outcome", False),
    ("converted", np.tile([0,1],20), "binary_outcome", True),
    ("is_conversion", np.tile([0,1],20), "binary_outcome", True),
    ("clicked", np.tile([0,1],20), "binary_outcome", True),
    ("holiday_period", np.tile([0,1],20), "binary_outcome", False),
    ("promotion", np.tile([0,1],20), "binary_outcome", False),
    ("is_mobile", np.tile([0,1],20), "binary_outcome", False),
    ("post_period", np.tile([0,1],20), "post", True),
    ("post_period", np.tile([0,1],20), "binary_outcome", False),
    ("variant", np.tile(["control","treatment"],20), "treatment", True),
    ("experiment_group", np.tile(["A","B"],20), "treatment", True),
    ("ad_spend", np.linspace(1,100,40), "spend", True),
    ("media_cost", np.linspace(1,100,40), "spend", True),
    ("revenue", np.linspace(100,300,40), "revenue", True),
    ("sales", np.linspace(100,300,40), "revenue", True),
    ("impressions", np.arange(100,140), "impressions", True),
    ("clicks", np.arange(10,50), "clicks", True),
    ("campaign_name", [f"c{i%4}" for i in range(40)], "campaign", True),
    ("placement", [f"p{i%3}" for i in range(40)], "campaign", True),
    ("source", ["google","meta"]*20, "channel", True),
    ("platform", ["google","meta"]*20, "channel", True),
    ("customer_id", [f"u{i}" for i in range(40)], "id", True),
    ("region", ["east","west"]*20, "segment", True),
]

@pytest.mark.parametrize("name,values,role,expected", ROLE_CASES)
def test_dataset_role_semantic_traps(name, values, role, expected):
    df = pd.DataFrame({name: values})
    intel = analyze_dataset_intelligence(df, "")
    assert (name in intel.role_map.get(role, [])) is expected

QUESTION_CASES = [
    ("Which channel has best ROAS?", ["channel","revenue"], "blocked"),
    ("Which channel has best ROAS?", ["channel","spend","revenue"], "provisionally_answerable"),
    ("What is CAC?", ["spend"], "blocked"),
    ("What is CAC?", ["spend","conversions"], "provisionally_answerable"),
    ("What caused conversion lift?", ["converted"], "blocked"),
    ("What caused conversion lift?", ["variant","converted"], "provisionally_answerable"),
    ("Predict churn", ["feature"], "blocked"),
    ("Predict churn", ["churned","feature"], "provisionally_answerable"),
    ("Compare revenue by channel", ["channel","revenue"], "provisionally_answerable"),
    ("Explore this dataset", ["feature"], "provisionally_answerable"),
]

def _df_for_roles(roles):
    n=80
    data={}
    if "channel" in roles: data["channel"]=["search","social"]*(n//2)
    if "spend" in roles: data["ad_spend"]=np.linspace(10,90,n)
    if "revenue" in roles: data["revenue"]=np.linspace(100,300,n)
    if "conversions" in roles: data["conversions"]=np.arange(n)%8
    if "variant" in roles: data["variant"]=["control","treatment"]*(n//2)
    if "converted" in roles: data["converted"]=[0,1]*(n//2)
    if "churned" in roles: data["churned"]=[0,1]*(n//2)
    if "feature" in roles: data["feature"]=np.linspace(0,1,n)
    return pd.DataFrame(data)

@pytest.mark.parametrize("question,roles,status", QUESTION_CASES)
def test_question_gate_cases(question, roles, status):
    intel=analyze_dataset_intelligence(_df_for_roles(roles), question)
    assert intel.question_assessment["status"] == status

# ---------------- MMM readiness + fit + optimization ----------------
def make_mmm(n=156, seed=123, effect=True):
    rng=np.random.default_rng(seed); t=np.arange(n)
    dates=pd.date_range("2023-01-01", periods=n, freq="W")
    a=100+25*np.sin(2*np.pi*t/26)+rng.normal(0,12,n)
    b=80+18*np.cos(2*np.pi*t/39)+rng.normal(0,10,n)
    promo=rng.binomial(1,.12,n)
    price=1+rng.normal(0,.02,n)
    base=1000+90*np.sin(2*np.pi*t/52)+120*promo-120*(price-1)
    y=base + ((1.8*a + 1.2*b) if effect else 0) + rng.normal(0,25,n)
    return pd.DataFrame({"week":dates,"revenue":y,"a_spend":a.clip(0),"b_spend":b.clip(0),"promo":promo,"price":price})

MMM_READINESS_MUTATIONS = [
    "good", "short_20", "short_60", "one_channel", "nine_channels", "thirteen_channels",
    "missing_media_1pct", "missing_media_5pct", "constant_outcome", "negative_media",
    "constant_media_one", "constant_media_all", "duplicate_dates", "irregular_80pct",
    "high_corr_80", "high_corr_99", "no_controls", "one_control", "two_controls",
    "nonnumeric_control", "infinite_outcome", "infinite_media", "zero_media_all", "all_zero_outcome",
]

@pytest.mark.parametrize("mutation", MMM_READINESS_MUTATIONS)
def test_mmm_readiness_red_team(mutation):
    df=make_mmm(); media=["a_spend","b_spend"]; controls=["promo","price"]
    if mutation=="short_20": df=df.iloc[:20].copy()
    elif mutation=="short_60": df=df.iloc[:60].copy()
    elif mutation=="one_channel": media=["a_spend"]
    elif mutation in {"nine_channels","thirteen_channels"}:
        k=9 if mutation=="nine_channels" else 13
        for i in range(2,k): df[f"m{i}"]=50+np.random.default_rng(i).normal(0,10,len(df))
        media=["a_spend","b_spend"]+[f"m{i}" for i in range(2,k)]
    elif mutation=="missing_media_1pct": df.loc[df.index[:2],"a_spend"]=np.nan
    elif mutation=="missing_media_5pct": df.loc[df.index[:10],"a_spend"]=np.nan
    elif mutation=="constant_outcome": df["revenue"]=1000
    elif mutation=="negative_media": df.loc[:5,"a_spend"]=-5
    elif mutation=="constant_media_one": df["a_spend"]=100
    elif mutation=="constant_media_all": df["a_spend"]=100; df["b_spend"]=80
    elif mutation=="duplicate_dates": df.loc[1,"week"]=df.loc[0,"week"]
    elif mutation=="irregular_80pct": df["week"]=pd.to_datetime(df["week"]); df.loc[::3,"week"] += pd.to_timedelta(2, unit="D")
    elif mutation=="high_corr_80": df["b_spend"]=(0.55*df["a_spend"]+np.random.default_rng(2).normal(0,20,len(df))).clip(lower=0)
    elif mutation=="high_corr_99": df["b_spend"]=df["a_spend"]*1.01
    elif mutation=="no_controls": controls=[]
    elif mutation=="one_control": controls=["promo"]
    elif mutation=="two_controls": pass
    elif mutation=="nonnumeric_control": df["promo_label"]=np.where(df["promo"]==1,"promo","none"); controls=["promo_label","price"]
    elif mutation=="infinite_outcome": df.loc[0,"revenue"]=np.inf
    elif mutation=="infinite_media": df.loc[0,"a_spend"]=np.inf
    elif mutation=="zero_media_all": df["a_spend"]=0; df["b_spend"]=0
    elif mutation=="all_zero_outcome": df["revenue"]=0
    r=mmm_readiness(df,"week","revenue",media,controls)
    if mutation in {"good","short_60","one_channel","nine_channels","high_corr_80","no_controls","one_control","two_controls"}:
        assert r.report.status in {"ready","caution"}
    elif mutation in {"short_20","thirteen_channels","missing_media_1pct","missing_media_5pct","constant_outcome","negative_media","constant_media_all","duplicate_dates","high_corr_99","nonnumeric_control","infinite_outcome","infinite_media","zero_media_all","all_zero_outcome"}:
        assert r.report.status == "blocked"
    elif mutation in {"constant_media_one","irregular_80pct"}:
        assert r.report.status in {"caution","blocked"}

@pytest.mark.parametrize("seed", list(range(10)))
def test_mmm_fit_is_finite_and_bounded(seed):
    df=make_mmm(seed=seed)
    out=fit_mmm(df,"week","revenue",["a_spend","b_spend"],["promo","price"])
    assert out["status"] == "Beta"
    assert 0 <= out["model"]["holdout_wape"] < 1
    assert math.isfinite(out["model"]["r2"])
    assert len(out["series"]) == len(df)
    assert set(out["channels"]) == {"a_spend","b_spend"}
    assert all(v["coefficient"] >= -1e-10 for v in out["channels"].values())

@pytest.mark.parametrize("budget_mult", [0.5,0.75,0.9,1.0,1.1,1.2,1.35,1.5])
def test_mmm_optimizer_budget_conservation(budget_mult):
    df=make_mmm(seed=55)
    out=fit_mmm(df,"week","revenue",["a_spend","b_spend"],["promo","price"])
    cur=sum(float(df[c].tail(8).mean()) for c in ["a_spend","b_spend"])
    budget=cur*budget_mult
    try:
        opt=optimize_budget(df,out,["a_spend","b_spend"],budget)
    except ValueError:
        # Larger budgets may correctly exceed historical support.
        assert budget_mult >= 1.2
        return
    assert abs(sum(opt["recommended"].values())-budget) < 1e-4
    assert all(v >= -1e-8 for v in opt["recommended"].values())

@pytest.mark.parametrize("alpha", [0.0,0.25,0.5,0.7,0.85])
def test_geometric_adstock_is_nonnegative_and_causal(alpha):
    x=np.array([10,0,0,0],float)
    y=geometric_adstock(x,alpha)
    assert np.all(y>=0)
    assert y[0]==10
    assert np.all(np.diff(y[1:])<=1e-12)

@pytest.mark.parametrize("scale", [0.1,1,10,100,1000])
def test_saturation_monotone_bounded(scale):
    x=np.linspace(0,1000,100)
    y=saturation(x,scale)
    assert np.all(np.diff(y)>=-1e-12)
    assert np.all((y>=0)&(y<=1))

# ---------------- Experimentation ----------------
BINARY_AB_CASES = [
    (1000,100,1000,100,"HOLD"),
    (10000,1000,10000,1200,"SHIP"),
    (10000,1200,10000,1000,"DON'T SHIP"),
    (100,1,100,5,"HOLD"),
    (100000,1000,100000,1100,"SHIP"),
    (500,0,500,10,"SHIP"),
    (500,10,500,0,"DON'T SHIP"),
    (5000,250,5000,255,"HOLD"),
]
@pytest.mark.parametrize("cn,cc,tn,tc,expected", BINARY_AB_CASES)
def test_binary_ab_directional_decisions(cn,cc,tn,tc,expected):
    r=analyze_binary_ab(cn,cc,tn,tc)
    assert r.verdict==expected
    assert 0<=r.p_value<=1 and 0<=r.fisher_p_value<=1
    assert r.ci_low<=r.absolute_lift<=r.ci_high

INVALID_BINARY = [
    (0,0,10,1),(-1,0,10,1),(10,-1,10,1),(10,11,10,1),(10,1,0,0),(10,1,10,11)
]
@pytest.mark.parametrize("args", INVALID_BINARY)
def test_binary_ab_rejects_invalid_counts(args):
    with pytest.raises(ValueError): analyze_binary_ab(*args)

@pytest.mark.parametrize("alpha", [0,-.1,1,1.1])
def test_binary_ab_rejects_invalid_alpha(alpha):
    with pytest.raises(ValueError): analyze_binary_ab(100,10,100,12,alpha=alpha)

@pytest.mark.parametrize("srm_alpha", [0,-.1,1,1.1])
def test_binary_ab_rejects_invalid_srm_alpha(srm_alpha):
    with pytest.raises(ValueError): analyze_binary_ab(100,10,100,12,srm_alpha=srm_alpha)

@pytest.mark.parametrize("baseline,target", [(0.02,0.025),(0.05,0.06),(0.1,0.12),(0.2,0.22),(0.5,0.55)])
def test_power_sample_size_positive(baseline,target):
    n=required_sample_size_per_group(baseline,target)
    assert isinstance(n,int) and n>0

@pytest.mark.parametrize("successes,n", [(0,10),(1,10),(5,10),(9,10),(10,10)])
def test_wilson_interval_contains_observed_rate(successes,n):
    lo,hi=wilson_interval(successes,n)
    p=successes/n
    assert -1e-12<=lo<=p+1e-12 and p-1e-12<=hi<=1+1e-12

@pytest.mark.parametrize("shift", [-2,-1,0,1,2])
def test_continuous_ab_direction(shift):
    rng=np.random.default_rng(900+shift)
    c=rng.normal(10,1,500); t=rng.normal(10+shift,1,500)
    r=analyze_continuous_ab(c,t)
    if shift>=1: assert r.decision=="SHIP"
    elif shift<=-1: assert r.decision=="DON'T SHIP"
    else: assert r.decision in {"HOLD","SHIP","DON'T SHIP"}
    assert r.ci_low<=r.absolute_lift<=r.ci_high

@pytest.mark.parametrize("alpha", [0,-.1,1,1.1])
def test_continuous_ab_rejects_invalid_alpha(alpha):
    with pytest.raises(ValueError): analyze_continuous_ab([1,2,3],[2,3,4],alpha=alpha)

# ---------------- Marketing / regression / ML / causal ----------------
@pytest.mark.parametrize("groups", [2,3,5,10])
def test_marketing_efficiency_group_counts(groups):
    rng=np.random.default_rng(groups); n=groups*50
    df=pd.DataFrame({"g":[f"g{i%groups}" for i in range(n)],"spend":rng.uniform(10,100,n),"revenue":rng.uniform(20,200,n),"conv":rng.integers(1,20,n),"clicks":rng.integers(10,100,n),"imp":rng.integers(1000,5000,n)})
    out=analyze_marketing_efficiency(df,"g","spend","revenue","conv","clicks","imp")
    assert out["totals"]["groups"]==groups
    assert len(out["rows"])==groups

@pytest.mark.parametrize("stages", [
    [1000,500],[1000,800,400],[1000,900,700,300],[500,250,125,60,30]
])
def test_funnel_monotone_counts(stages):
    df=pd.DataFrame({f"s{i}":[v] for i,v in enumerate(stages)})
    out=analyze_funnel(df,list(df.columns))
    assert len(out["stages"])==len(stages)
    for row in out["stages"][1:]: assert 0<=row["step_conversion"]<=1

@pytest.mark.parametrize("seed", list(range(5)))
def test_linear_regression_recovers_signal(seed):
    rng=np.random.default_rng(seed); n=500; x=rng.normal(size=n); z=rng.normal(size=n); y=3+2*x-.5*z+rng.normal(0,.5,n)
    out=fit_linear_regression(pd.DataFrame({"y":y,"x":x,"z":z}),"y",["x","z"])
    coeff={r["term"]:r["coefficient"] for r in out["coefficients"]}
    assert abs(coeff["x"]-2)<.15
    assert abs(coeff["z"]+.5)<.15
    assert out["r2"]>.85

@pytest.mark.parametrize("seed", list(range(5)))
def test_logistic_regression_has_reasonable_discrimination(seed):
    rng=np.random.default_rng(100+seed); n=1000; x=rng.normal(size=n); logits=1.5*x; p=1/(1+np.exp(-logits)); y=rng.binomial(1,p)
    out=fit_logistic_regression(pd.DataFrame({"y":y,"x":x}),"y",["x"])
    assert .7 < out["auc_in_sample"] <= 1
    assert 0 <= out["brier_in_sample"] <= .25

@pytest.mark.parametrize("task", ["classification","regression"])
def test_tree_model_holdout_metrics_exist(task):
    rng=np.random.default_rng(222); n=600; x=rng.normal(size=n); cat=rng.choice(["a","b","c"],n)
    if task=="classification": y=(x+rng.normal(0,.5,n)>0).astype(int)
    else: y=2*x+rng.normal(0,.5,n)
    out=fit_tree_model(pd.DataFrame({"y":y,"x":x,"cat":cat}),"y",["x","cat"],task=task)
    assert out["n_train"]+out["n_holdout"]==n
    assert out["metrics"]

@pytest.mark.parametrize("effect", [-10,-5,0,5,10])
def test_did_recovers_known_effect(effect):
    rng=np.random.default_rng(333+effect); units=40; periods=8
    rows=[]
    for u in range(units):
        tr=int(u>=units//2)
        for t in range(periods):
            post=int(t>=4)
            y=100+u*.1+t*2+effect*tr*post+rng.normal(0,1)
            rows.append((u,tr,post,y))
    df=pd.DataFrame(rows,columns=["unit","treat","post","y"])
    out=run_difference_in_differences(df,"y","treat","post",unit_col="unit")
    assert abs(out["effect"]-effect)<1.0

@pytest.mark.parametrize("level,slope", [(0,0),(5,0),(-5,0),(0,1),(0,-1)])
def test_its_direction(level,slope):
    rng=np.random.default_rng(444); n=80; t=np.arange(n); post=(t>=40).astype(int); after=np.maximum(0,t-40)
    y=100+.5*t+level*post+slope*after+rng.normal(0,.5,n)
    df=pd.DataFrame({"date":pd.date_range("2024-01-01",periods=n,freq="W"),"y":y})
    out=run_interrupted_time_series(df,"y","date",str(df.loc[40,"date"].date()))
    assert abs(out["level_change"]-level)<1.5
    assert abs(out["slope_change"]-slope)<.15

@pytest.mark.parametrize("statistic", ["mean","median"])
def test_bootstrap_detects_shift(statistic):
    rng=np.random.default_rng(555); c=rng.normal(0,1,200); t=rng.normal(1,1,200)
    df=pd.DataFrame({"g":["c"]*200+["t"]*200,"y":np.r_[c,t]})
    out=bootstrap_group_difference(df,"g","y","c","t",statistic=statistic,iterations=500)
    assert out["effect"]>.6
    assert out["ci_low"]>0

@pytest.mark.parametrize("outcome_type", ["binary","continuous"])
def test_abn_three_arms(outcome_type):
    rng=np.random.default_rng(666); n=300; g=np.repeat(["A","B","C"],n//3)
    if outcome_type=="binary": y=np.r_[rng.binomial(1,.1,n//3),rng.binomial(1,.15,n//3),rng.binomial(1,.2,n//3)]
    else: y=np.r_[rng.normal(0,1,n//3),rng.normal(.5,1,n//3),rng.normal(1,1,n//3)]
    out=analyze_abn(pd.DataFrame({"g":g,"y":y}),"g","y",outcome_type=outcome_type,control_group="A")
    assert len(out["arms"])==3
    assert len(out["pairwise_vs_control"])==2
