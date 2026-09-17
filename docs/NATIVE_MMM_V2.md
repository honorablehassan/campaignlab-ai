# Native MMM V2 Beta

Native V2 is CampaignLab's fast deterministic MMM engine. It does not claim parity with a fully Bayesian engine.

## Added in V2

- exponential and Hill saturation candidates;
- multiple scale and slope candidates per channel;
- geometric carryover selection on training history;
- rolling validation for the regularization penalty inside the training window;
- one untouched final chronological holdout;
- expanding-window backtests so one favorable final period cannot establish stability;
- baseline-with-controls holdout benchmark;
- leave-one-control-out contribution sensitivity;
- non-negative media coefficients;
- residual block-bootstrap contribution intervals;
- explicit interval-scope warning;
- historically bounded budget optimization across the selected response family;
- Native V2 evidence provenance in the Decision Object.
- optional precision-weighted experiment calibration for a named channel and spend contrast, with explicit scope and uncertainty provenance.

## Remaining limitations

- response transformations are selected deterministically, not jointly sampled;
- bootstrap intervals are conditional on the selected transformation;
- no posterior distribution or Bayesian prior system;
- no geo hierarchy or reach/frequency model;
- experiment calibration is deterministic and contrast-specific, not a jointly estimated Bayesian prior system;
- observational identification remains the dominant limitation.

The future Meridian adapter should be an additional engine, not a silent replacement. CampaignLab must preserve engine identity and uncertainty provenance when arbitrating results.
