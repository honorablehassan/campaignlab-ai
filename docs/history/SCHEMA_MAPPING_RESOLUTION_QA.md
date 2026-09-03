# Consequential Schema Mapping Resolution

## Problem fixed
The Data Builder could detect ambiguity but the general Evidence Data UI could not resolve it as a single downstream analytical contract. A cosmetic dropdown would have been unsafe because Dataset Intelligence, method ranking, and tool execution could still disagree.

## New contract
For consequential ambiguous roles such as revenue, spend, date, conversions, event, user, and session:

1. Data Builder surfaces the ambiguity.
2. The user can confirm the intended field or explicitly leave it unresolved.
3. `analyze_dataset_intelligence(..., role_overrides=...)` makes the confirmed role sovereign and removes other inferred candidates for that role.
4. Explicitly unresolved roles are removed from downstream eligibility rather than guessed.
5. `rank_methods` consumes the resolved Dataset Intelligence object.
6. visualization planning consumes the same resolved intelligence.
7. `EvidenceToolRuntime(..., role_overrides=...)` uses the same contract for its own intelligence/ranking calls.
8. Runtime execution rejects contradictory confirmed mappings for supported consequential tool arguments.
9. UI result signatures include the mapping, so changing gross→net revenue invalidates the old result.

## Product language
The UI says: "One thing CampaignLab won't guess." It explains that the choice is used for readiness, method selection, charts and analysis.

## Validation
661 tests pass, including new tests for ambiguity detection, resolved propagation, unresolved fail-closed behavior, invalid mapping rejection, and runtime contradiction rejection.
