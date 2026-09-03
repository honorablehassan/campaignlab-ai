from __future__ import annotations

from dataclasses import dataclass, asdict
import math
import numpy as np
from scipy import stats


@dataclass(frozen=True)
class ContinuousABResult:
    control_n: int
    treatment_n: int
    control_mean: float
    treatment_mean: float
    absolute_lift: float
    relative_lift: float | None
    ci_low: float
    ci_high: float
    p_value: float
    welch_df: float
    cohen_d: float
    mann_whitney_p: float | None
    decision: str
    practical_significance: str
    warnings: list[str]

    def to_dict(self):
        return asdict(self)


def _validate(x, y):
    a = np.asarray(x, dtype=float)
    b = np.asarray(y, dtype=float)
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if len(a) < 2 or len(b) < 2:
        raise ValueError("Each group needs at least two finite observations.")
    return a, b


def analyze_continuous_ab(control, treatment, alpha: float = 0.05, business_threshold: float = 0.0) -> ContinuousABResult:
    if not 0 < alpha < 1:
        raise ValueError("Alpha must be between 0 and 1.")
    if business_threshold < 0:
        raise ValueError("Business threshold cannot be negative.")
    c, t = _validate(control, treatment)
    mc, mt = float(c.mean()), float(t.mean())
    vc, vt = float(c.var(ddof=1)), float(t.var(ddof=1))
    nc, nt = len(c), len(t)
    se = math.sqrt(vc/nc + vt/nt)
    diff = mt - mc
    if se == 0:
        p = 1.0 if diff == 0 else 0.0
        df = float("inf")
        ci = (diff, diff)
    else:
        num = (vc/nc + vt/nt) ** 2
        den = (vc/nc) ** 2 / max(1, nc-1) + (vt/nt) ** 2 / max(1, nt-1)
        df = num / den if den > 0 else float("inf")
        crit = stats.t.ppf(1-alpha/2, df)
        ci = (diff-crit*se, diff+crit*se)
        p = float(2*stats.t.sf(abs(diff/se), df))
    pooled_den = max(1, nc+nt-2)
    pooled_sd = math.sqrt(((nc-1)*vc + (nt-1)*vt)/pooled_den)
    d = diff/pooled_sd if pooled_sd > 0 else 0.0
    try:
        mw_p = float(stats.mannwhitneyu(c, t, alternative="two-sided").pvalue)
    except Exception:
        mw_p = None
    warnings=[]
    if min(nc,nt) < 30:
        warnings.append("At least one group has fewer than 30 observations; inspect distribution/outliers carefully.")
    if max(abs(stats.skew(c)), abs(stats.skew(t))) > 2:
        warnings.append("Outcome is strongly skewed; use the Mann–Whitney cross-check and consider a robust/bootstrapped analysis.")
    threshold = max(0.0, float(business_threshold))
    if ci[0] > threshold:
        decision = "SHIP"
        practical = "Evidence supports a positive effect above the business threshold."
    elif ci[1] < -threshold:
        decision = "DON'T SHIP"
        practical = "Evidence supports a harmful effect beyond the business threshold."
    else:
        decision = "HOLD"
        practical = "The interval overlaps the decision threshold; evidence is not decisive enough."
    return ContinuousABResult(
        control_n=nc, treatment_n=nt, control_mean=mc, treatment_mean=mt,
        absolute_lift=diff, relative_lift=(diff/mc if mc != 0 else None),
        ci_low=float(ci[0]), ci_high=float(ci[1]), p_value=float(p), welch_df=float(df),
        cohen_d=float(d), mann_whitney_p=mw_p, decision=decision,
        practical_significance=practical, warnings=warnings,
    )
