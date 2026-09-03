# Evidence Lab workflow fix

The prior UI improved terminology but still made uncertainty a dead end. This patch changes the design flow from method-prerequisite-first to recommendation-first.

## New flow

1. User states the uncertainty.
2. User names the business outcome in ordinary language.
3. User describes what can actually vary in the real world.
4. CampaignLab builds a useful evidence plan for every branch, including "I'm not sure yet".
5. Only when a supported deterministic calculator needs a specific measurement shape does CampaignLab ask for it.
6. Existing evidence routes forward to Analyze Results or Analyze Data.
7. Stale plans are invalidated when inputs change.

## Product rule

The user brings the uncertainty. CampaignLab performs the analytical translation.
