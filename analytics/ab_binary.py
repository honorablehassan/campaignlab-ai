from __future__ import annotations

from dataclasses import asdict, dataclass
from math import ceil, sqrt

from scipy.stats import binomtest, fisher_exact, norm


@dataclass(frozen=True)
class BinaryABResult:
    control_n: int
    control_conversions: int
    treatment_n: int
    treatment_conversions: int
    control_rate: float
    treatment_rate: float
    absolute_lift: float
    relative_lift: float | None
    z_statistic: float
    p_value: float
    fisher_p_value: float
    ci_low: float
    ci_high: float
    control_ci_low: float
    control_ci_high: float
    treatment_ci_low: float
    treatment_ci_high: float
    expected_treatment_n: float
    srm_p_value: float
    srm_status: str
    alpha: float
    business_threshold: float
    verdict: str
    verdict_reason: str
    robustness_status: str
    achieved_power_at_observed_effect: float | None

    def to_dict(self) -> dict:
        return asdict(self)


def _validate_counts(n: int, conversions: int, label: str) -> None:
    if n <= 0:
        raise ValueError(f"{label} sample size must be greater than zero.")
    if conversions < 0 or conversions > n:
        raise ValueError(f"{label} conversions must be between 0 and sample size.")


def wilson_interval(successes: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    _validate_counts(n, successes, "Group")
    if not 0 < alpha < 1:
        raise ValueError("Alpha must be between 0 and 1.")
    z = norm.ppf(1 - alpha / 2)
    p = successes / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    spread = (z / denom) * sqrt((p * (1 - p) / n) + (z**2 / (4 * n**2)))
    return max(0.0, center - spread), min(1.0, center + spread)


def newcombe_difference_interval(
    control_successes: int,
    control_n: int,
    treatment_successes: int,
    treatment_n: int,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Newcombe hybrid-score CI for treatment minus control proportions."""
    p0 = control_successes / control_n
    p1 = treatment_successes / treatment_n
    l0, u0 = wilson_interval(control_successes, control_n, alpha)
    l1, u1 = wilson_interval(treatment_successes, treatment_n, alpha)
    diff = p1 - p0
    low = diff - sqrt((p1 - l1) ** 2 + (u0 - p0) ** 2)
    high = diff + sqrt((u1 - p1) ** 2 + (p0 - l0) ** 2)
    return low, high


def required_sample_size_per_group(
    baseline_rate: float,
    target_rate: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    """Approximate equal-allocation sample size per group for two proportions."""
    if not 0 < baseline_rate < 1 or not 0 < target_rate < 1:
        raise ValueError("Baseline and target conversion rates must be between 0 and 1.")
    if baseline_rate == target_rate:
        raise ValueError("Target rate must differ from baseline rate.")
    if not 0 < alpha < 1 or not 0 < power < 1:
        raise ValueError("Alpha and power must be between 0 and 1.")

    p_bar = (baseline_rate + target_rate) / 2
    z_alpha = norm.ppf(1 - alpha / 2)
    z_beta = norm.ppf(power)
    numerator = (
        z_alpha * sqrt(2 * p_bar * (1 - p_bar))
        + z_beta
        * sqrt(
            baseline_rate * (1 - baseline_rate)
            + target_rate * (1 - target_rate)
        )
    ) ** 2
    denominator = (target_rate - baseline_rate) ** 2
    return ceil(numerator / denominator)


def approximate_power_two_proportions(
    control_rate: float,
    treatment_rate: float,
    n_control: int,
    n_treatment: int,
    alpha: float = 0.05,
) -> float | None:
    """Normal-approximation power for a two-sided two-proportion comparison."""
    effect = abs(treatment_rate - control_rate)
    if effect == 0:
        return alpha
    if min(n_control, n_treatment) <= 0:
        return None

    pooled = (control_rate * n_control + treatment_rate * n_treatment) / (
        n_control + n_treatment
    )
    se0 = sqrt(pooled * (1 - pooled) * (1 / n_control + 1 / n_treatment))
    se1 = sqrt(
        control_rate * (1 - control_rate) / n_control
        + treatment_rate * (1 - treatment_rate) / n_treatment
    )
    if se0 == 0 or se1 == 0:
        return None
    critical = norm.ppf(1 - alpha / 2) * se0
    # Probability, under the alternative, of landing beyond either null critical bound.
    upper = 1 - norm.cdf((critical - effect) / se1)
    lower = norm.cdf((-critical - effect) / se1)
    return max(0.0, min(1.0, upper + lower))


def analyze_binary_ab(
    control_n: int,
    control_conversions: int,
    treatment_n: int,
    treatment_conversions: int,
    *,
    alpha: float = 0.05,
    expected_treatment_share: float = 0.50,
    srm_alpha: float = 0.01,
    business_threshold: float = 0.0,
) -> BinaryABResult:
    """Run a deterministic binary A/B analysis with integrity and robustness checks."""
    _validate_counts(control_n, control_conversions, "Control")
    _validate_counts(treatment_n, treatment_conversions, "Treatment")
    if not 0 < alpha < 1:
        raise ValueError("Alpha must be between 0 and 1.")
    if not 0 < srm_alpha < 1:
        raise ValueError("SRM alpha must be between 0 and 1.")
    if not 0 < expected_treatment_share < 1:
        raise ValueError("Expected treatment allocation must be between 0 and 1.")
    if business_threshold < 0:
        raise ValueError("Business threshold cannot be negative.")

    p0 = control_conversions / control_n
    p1 = treatment_conversions / treatment_n
    diff = p1 - p0
    relative = diff / p0 if p0 > 0 else None

    pooled = (control_conversions + treatment_conversions) / (control_n + treatment_n)
    pooled_se = sqrt(pooled * (1 - pooled) * (1 / control_n + 1 / treatment_n))
    z_stat = diff / pooled_se if pooled_se > 0 else 0.0
    p_value = 2 * (1 - norm.cdf(abs(z_stat))) if pooled_se > 0 else 1.0

    table = [
        [treatment_conversions, treatment_n - treatment_conversions],
        [control_conversions, control_n - control_conversions],
    ]
    fisher_p = float(fisher_exact(table, alternative="two-sided").pvalue)

    control_ci = wilson_interval(control_conversions, control_n, alpha)
    treatment_ci = wilson_interval(treatment_conversions, treatment_n, alpha)
    diff_ci = newcombe_difference_interval(
        control_conversions,
        control_n,
        treatment_conversions,
        treatment_n,
        alpha,
    )

    total_n = control_n + treatment_n
    observed_treatment_n = treatment_n
    srm = binomtest(
        observed_treatment_n,
        total_n,
        expected_treatment_share,
        alternative="two-sided",
    )
    srm_p = float(srm.pvalue)
    srm_status = "pass" if srm_p >= srm_alpha else "fail"

    z_sig = p_value < alpha
    fisher_sig = fisher_p < alpha
    direction_agrees = diff_ci[0] > 0 if diff > 0 else diff_ci[1] < 0 if diff < 0 else True
    if srm_status == "fail":
        robustness = "integrity_risk"
    elif z_sig == fisher_sig and (not z_sig or direction_agrees):
        robustness = "robust"
    else:
        robustness = "fragile"

    threshold = business_threshold
    if srm_status == "fail":
        verdict = "HOLD"
        reason = (
            "Traffic allocation differs enough from the expected split to trigger a "
            "sample-ratio-mismatch warning. Validate assignment/logging before acting."
        )
    elif diff_ci[0] >= threshold and diff > 0:
        verdict = "SHIP"
        reason = (
            "The plausible treatment effect clears the minimum commercially worthwhile "
            "lift under the current confidence level."
        )
    elif diff_ci[1] < threshold:
        verdict = "DON'T SHIP"
        reason = (
            "Even the optimistic end of the confidence interval does not clear the "
            "minimum commercially worthwhile lift."
        )
    else:
        verdict = "HOLD"
        reason = (
            "The evidence does not yet separate a commercially worthwhile improvement "
            "from a weak or null effect with enough confidence."
        )

    power = approximate_power_two_proportions(p0, p1, control_n, treatment_n, alpha)

    return BinaryABResult(
        control_n=control_n,
        control_conversions=control_conversions,
        treatment_n=treatment_n,
        treatment_conversions=treatment_conversions,
        control_rate=p0,
        treatment_rate=p1,
        absolute_lift=diff,
        relative_lift=relative,
        z_statistic=z_stat,
        p_value=p_value,
        fisher_p_value=fisher_p,
        ci_low=diff_ci[0],
        ci_high=diff_ci[1],
        control_ci_low=control_ci[0],
        control_ci_high=control_ci[1],
        treatment_ci_low=treatment_ci[0],
        treatment_ci_high=treatment_ci[1],
        expected_treatment_n=total_n * expected_treatment_share,
        srm_p_value=srm_p,
        srm_status=srm_status,
        alpha=alpha,
        business_threshold=threshold,
        verdict=verdict,
        verdict_reason=reason,
        robustness_status=robustness,
        achieved_power_at_observed_effect=power,
    )
