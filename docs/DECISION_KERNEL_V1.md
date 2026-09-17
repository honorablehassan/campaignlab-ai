# Decision Kernel V1

## Purpose

CampaignLab's labs are entry points. The Decision Object is the shared destination.

V1 standardizes:

- the call and action posture;
- confidence score, label, and basis;
- supporting and contradicting evidence;
- assumptions and alternatives;
- critical uncertainty and flip conditions;
- whether more evidence is worth obtaining;
- the smallest useful next check;
- predicted and actual outcomes;
- deterministic/AI provenance and warnings.

## Product behavior

The kernel does not replace Strategy Lab, Evidence Lab, or the MMM workspace. It sits beneath their existing outputs and makes decisions portable and auditable.

Strategy confidence is bounded because it is structured reasoning rather than measured causal evidence. Red-team, comparison, and scenario results can raise or lower confidence, but cannot manufacture statistical certainty.

Native MMM confidence combines readiness, chronological holdout performance, and improvement over a baseline-with-controls model. It cannot become High in V1 because the native MMM remains observational.

## Memory scope

Decision Memory V1 uses Streamlit session state. This is appropriate for a pre-account Beta and avoids quietly writing sensitive decisions to a shared local file. Users can export one decision or the full session memory as JSON.

Persistent multi-user memory requires authentication, authorization, a database, retention/deletion controls, and an audit trail. Those are deliberately not simulated in V1.

## Next integrations

1. Give Evidence Lab's orchestrator a structured Decision Object output rather than parsing prose.
2. Add outcome check-ins and confidence-calibration summaries after persistence exists.
3. Make the future Meridian adapter emit the same evidence and decision contracts as Native MMM V2.
4. Add the Decision Object to PDF and analyst exports.
