# CampaignLab AI

**Where marketing ideas face reality.**

CampaignLab is an AI marketing decision system with two connected layers:

- **Strategy Lab** makes, compares, stress-tests, and scenario-tests a strategic call.
- **Evidence Lab** inspects data, checks what the evidence can support, selects from registered analytical methods, executes deterministic Python tools, visualizes the decision, and lets the LLM explain the result without inventing statistics.

## Evidence Lab: live analytical horsepower

CampaignLab's current Live deterministic executors include:

- Binary A/B testing with Wilson/Newcombe intervals, Fisher cross-check, SRM and business-threshold decisions
- Continuous A/B testing with Welch inference, effect size and Mann–Whitney robustness check
- A/B/n multi-arm testing with omnibus tests and Holm multiple-comparison correction
- Bootstrap mean/median group differences
- Linear regression with HC3 robust SE, VIF, heteroskedasticity check and fit metrics
- Logistic regression with odds ratios, convergence/separation safeguards, AUC and Brier score
- Random Forest / Gradient Boosting predictive models with holdout evaluation and feature importance
- Marketing efficiency: ROAS, CPA, CPC, CPM, CTR, CVR and spend share
- Funnel analysis
- Cohort / retention analysis
- Difference-in-Differences with robust or unit-clustered SE
- Panel event study with unit/time fixed effects and clustered SE
- Interrupted time series with HAC standard errors
- K-means segmentation with silhouette-based automatic k selection
- Isolation Forest anomaly detection

The **Analytics Directory** is generated from the same capability registry used by Evidence Lab. A method is not labeled Live merely because the LLM knows what it is.

Advanced methods such as synthetic control, DAG-guided adjustment, DML and causal forests are documented with Research status and are not falsely represented as executed.

## Architecture

`Python calculates. AI reasons and explains.`

Raw uploaded DataFrames remain server-side. The Evidence Orchestrator can only invoke whitelisted deterministic tools. It cannot execute arbitrary Python or SQL. Dataset intelligence runs before LLM interpretation and compresses schema, data-quality findings, semantic roles, answerability and method eligibility into structured evidence.

## Reliability and observability

- bounded OpenAI retries and timeout
- safe UI error boundary and reference IDs
- tool-level failure isolation
- session telemetry for model/tool calls, latency, tokens and estimated cost
- no raw uploaded rows written to telemetry
- strict JSON schemas for Strategy outputs
- source package excludes `.venv`, `.git`, caches and secrets
- automated deterministic engine tests

## Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
```

For development and test dependencies:

```bash
pip install -r requirements-dev.txt
```

Create `.streamlit/secrets.toml` locally:

```toml
OPENAI_API_KEY = "your-key-here"
```

Never commit this file.

Run tests:

```bash
python -m pytest -q
```

Run CampaignLab:

```bash
streamlit run app.py
```

Two synthetic demo datasets are included in `examples/`.


## Product Experience V2
- Interactive Plotly Decision Chartbook (Matplotlib remains as deterministic fallback/export support)
- Executive / Analyst view modes
- Registry-grounded plain-English method explainers
- PDF Decision Report export
- Behind the Lab / Support CampaignLab coming-soon page
- Plan vs Call terminology guardrail
- Ask CampaignLab about the current result (on-demand, context-bounded follow-up)

## V2.5 Lab Special: Marketing Mix & Budget Optimizer (Beta)
Open **Lab Special: MMM** from CampaignLab navigation or the homepage feature card. Load `examples/demo_mmm_weekly.csv` to exercise the full deterministic workflow.
