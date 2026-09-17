# CampaignLab Release Audit Protocol

Every capability iteration must pass this audit before it can be packaged.

## 1. Regression gate

- Full automated test suite passes.
- Active Python modules compile.
- Git diff contains only intended changes.
- Clean checkout starts without a secrets file.
- No secret or generated environment is included in the package.

## 2. Workflow gate

- Every top-level page renders.
- A/B results complete from inputs to decision.
- Uploaded demo data completes recognition, mapping and method selection.
- MMM demo completes readiness, fitting, validation, optimization and decision.
- Stale input/result protection remains intact.

## 3. Decision-coherence gate

- One workflow produces one canonical Decision Object.
- No older UI block competes with the canonical call.
- Deterministic claims originate in a validated analytical result envelope.
- AI explanation remains subordinate to deterministic evidence.
- UI, JSON, PDF and memory use the same Decision Object where implemented.

## 4. Product-identity gate

- Strategy Lab, Evidence Lab and Lab Specials retain their roles.
- Python calculates; AI reasons and explains.
- Uncertainty changes confidence and posture rather than automatically blocking action.
- Unsupported causality is never implied.
- CampaignLab still converges toward a defensible call.

## Release language

Each handoff must distinguish:

- implemented
- automatically tested
- manually exercised
- visually verified
- planned

Passing tests alone never establishes visual quality, statistical validity or commercial readiness.
