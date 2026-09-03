# CampaignLab AI — Product Constitution

## Thesis
CampaignLab is an AI marketing decision system, not a brainstorming chatbot.

> Don't hallucinate certainty. Calculate what can be calculated, cite what can be evidenced, label what is assumed, and experiment on what remains uncertain.

## Core loop
UNDERSTAND → INGEST → GENERATE → QUANTIFY → CHALLENGE → IDENTIFY UNCERTAINTY → EXPERIMENT / ANALYZE → DECIDE

## Product surfaces

### 🧠 Strategy Lab
Makes the best available strategic call, then exposes assumptions, risks, serious alternatives, adversarial critique, scenario pressure points, and what evidence could change the call.

### 🔬 Evidence Lab
Question-first analysis through three entry paths: no data yet, experiment results, or uploaded data. Python owns deterministic calculation. The LLM selects registered tools, interprets structured evidence and explains the decision.

### 📚 Analytics Directory
The transparent capability map. It reads from the same Method Registry as Evidence Lab and explains status, use cases, evidence requirements, assumptions, diagnostics, outputs, visuals and cautions.

### ⚙️ System Health
Developer/portfolio observability for model calls, tool calls, errors, latency, tokens and estimated API cost. This is operational telemetry, not customer evidence.

## Non-negotiable analytical boundary
**Python calculates. AI reasons and explains.**

No LLM-generated p-values, confidence intervals, sample sizes, model metrics or uploaded-data statistics when a deterministic tool exists. No arbitrary Python/SQL tool execution. No method is Live until its executable contract, guardrails and tests exist.

## Decision rule
CampaignLab should make the strongest decision justified by the evidence, but must never manufacture a causal conclusion the data cannot support.

### Lab Specials
Lab Specials are heavier end-to-end analytical products that deserve dedicated workspaces rather than making Evidence Lab noisy. The first is Marketing Mix & Budget Optimizer (Beta). It follows the same product constitution: deterministic calculation, explicit readiness, uncertainty/trust guardrails, and no causal certainty beyond what the evidence supports.
