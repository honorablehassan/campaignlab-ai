# Decision Output V2

Decision Output V2 makes the Decision Object the authority across Strategy Lab, Evidence Lab and the native MMM.

## Analytical result envelope

Deterministic tools preserve their full method-specific output and add a closed common envelope containing:

- estimand
- estimate and units
- uncertainty
- business verdict and threshold
- integrity checks
- assumptions and warnings
- deterministic provenance

The common envelope is not a replacement for method-specific diagnostics. It is the safe interface between calculation and decision reasoning.

## Evidence Lab convergence

The direct binary A/B workflow now derives a Decision Object from the deterministic result. Tool-orchestrated analyses carry their analytical envelope through the audit trace, allowing the Evidence Lab UI, memory and PDF to use the same decision authority.

If no deterministic analysis executed, the Decision Object is explicitly marked as an investigation plan with low confidence. It cannot masquerade as an evidence-backed call.

## Preserved boundaries

- Raw uploaded rows do not enter LLM tool arguments.
- Method-specific outputs remain available.
- Observational evidence does not become causal merely because it enters the Decision Kernel.
- Strategy reasoning remains identified as AI reasoning rather than deterministic computation.

## Evidence arbitration

When more than one deterministic analysis executes, CampaignLab ranks the evidence using explicit identification and diagnostic rules. Randomized evidence starts above quasi-experimental evidence, which starts above observational, attribution, predictive and descriptive evidence. Failed integrity checks can demote otherwise strong methods.

CampaignLab separately detects:

- agreement on the same estimand
- directional agreement across different estimands
- conflicting directions or decision verdicts
- evidence that is not safe to compare

Conflicting evidence lowers confidence and names the smallest next check. Numerical results with different estimands are never silently averaged.
