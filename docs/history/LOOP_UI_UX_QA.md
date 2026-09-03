# CampaignLab — Full Product Loop UI/UX QA

Baseline audited: current build after the Evidence Lab workflow fix + Behind the Lab visual fix.

This round treats regression tests as a seatbelt, not proof of good UX. The audit followed complete user loops and attacked stale state, dead ends, context loss, hidden assumptions, over-promising, and visual/product semantics.

## Personas used
- First-time founder/operator
- CMO / marketing leader
- Growth marketer
- Marketing analyst
- Data scientist / statistician
- Warehouse / analytics-engineering user
- Returning power user
- Skeptical reviewer trying to catch overclaiming

## Loops audited
1. Home → Strategy → Call → Compare / Devil's Advocate / Scenario → Evidence handoff
2. Evidence → Create evidence → unsure / individual / group / time / already happened
3. Evidence → Existing results → decision
4. Evidence → Data → understanding → question → method → charts → orchestration → report / follow-up
5. Analytics Directory → method discovery → actual workspace
6. MMM → data → mapping → readiness → model → allocation → decision → Evidence validation
7. Behind the Lab → founder story → support rail
8. Backtracking and edited-input behavior across every stateful result

## P0 / trust failures found and fixed

### 1. Strategy could show an old recommendation under edited inputs
A user could run Strategy, then change the product/objective/budget/context and still see the old Call until they submitted again.

Fix: Strategy now detects edited upstream inputs and hides the stale result until CampaignLab is rerun.

### 2. Strategy Arena, Devil's Advocate, and Scenario Lab could show old outputs after the user changed the challenger / attack focus / scenario
Fix: each follow-up now stores and compares an input signature. Edited controls invalidate the visible old result.

### 3. Manual A/B results could remain visible after counts, split, or business threshold changed
Fix: result signature guard added. CampaignLab asks for a rerun instead of showing an old statistical verdict beneath new numbers.

### 4. Data analysis could remain visible when the question changed, or when a different file reused the same filename
Fix: orchestration is now keyed to a deterministic dataset fingerprint + question, not just the filename.

### 5. MMM could show old attribution / optimizer outputs after the dataset or model mapping changed
Fix: MMM model output is now keyed to dataset fingerprint + date/outcome/media/control mapping. Any change forces a rerun before old conclusions are shown.

## P1 / mental-model and workflow failures found and fixed

### 6. Strategy still described itself as solving a “marketing problem” after the brand broadened
Fix: hero now says “messy decision.” The Evidence handoff copy no longer refers to the retired Experiment Lab framing.

### 7. Strategy → Evidence context handoff could fail for returning users
The handoff populated helper state, but the actual Evidence widget keys could still contain an older question from a prior visit.

Fix: handoffs now populate the real widget keys, clear old Evidence plans/sizing outputs, set the Evidence route, and navigate directly to Evidence Lab.

Also fixed: Strategy no longer pretends a broad objective such as “Grow Revenue” is automatically the primary measured outcome. Evidence asks for the real metric.

### 8. Evidence “I’m not sure” still felt like a routing memo rather than a forward path
Fix: the Create Evidence CTA is now “Find My Evidence Path.” The unsure branch gives an explicit route to bring whatever evidence already exists. Every ordinary branch has a next action.

### 9. “I already ran a test” had a dead-end for anything other than binary A/B summaries
Fix: unsupported summary-only test types now route the user to bring raw experiment data so CampaignLab can identify the supported analytical path instead of stopping.

### 10. Blocked dataset questions could still present an “Analyze this decision” CTA
Fix: blocked questions now become “Show me what would unlock this question.” The orchestrator is instructed to explain the evidence gap and nearest defensible analysis, not pretend the blocked question was answered.

### 11. Analytics Directory quietly defaulted every visitor into Experimentation & Uplift
This reinforced the exact “CampaignLab is basically an experiment app” mental model we are trying to avoid.

Fix: no family is preselected. The first view shows all decision families and explicitly says to choose the question, not the technique.

### 12. Analytics Directory was still partly a museum
Ready methods explained themselves but had no strong loop into actual use.

Fix: Live methods now include “Use this with my data →” and carry the method interest into Evidence Lab. MMM routes to its guarded workspace.

### 13. MMM → Evidence lost context
The prior link simply opened Evidence Lab.

Fix: MMM now carries the working allocation decision, confidence, causal caveat, outcome, and best next evidence into Evidence Lab.

### 14. MMM hardcoded “weekly” in the budget decision even when the data could be monthly or another regular period
Fix: UI infers the period from the built dataset / date spacing and labels allocation as per day / week / month / period. The model itself is unchanged.

### 15. MMM hardcoded USD visuals
Fix: display currency is now explicit and can remain “Source units.” This is a display setting only and does not alter the model.

### 16. MMM mapping UI ignored some of CampaignLab’s own source understanding
Fix: likely date, outcome, and spend mappings from the deterministic source-understanding layer now seed the visible selectors when available.

## P2 / coherence improvements included
- Analytics Directory status counts are condensed instead of repeating the status legend with four large metric tiles.
- Evidence carried context can be explicitly cleared.
- Strategy’s “What CampaignLab Would Test” is reframed as “What Would Reduce the Uncertainty,” keeping Evidence broader than experimentation.
- Create Evidence copy now promises only validated design calculators rather than implying every experimental family is already fully runnable.

## Important remaining product gap — not hidden

### Consequential schema ambiguity still needs a real mapping-resolution interaction
Data Builder can deterministically detect ambiguous fields and correctly refuses to pretend certainty. But the general Evidence Data UI still does not yet have a first-class field-mapping override that flows through Dataset Intelligence + Method Ranker + Tool Runtime as a single resolved contract.

That should be its own bounded feature, not a cosmetic dropdown whose answer is ignored downstream.

Until that exists, CampaignLab should continue surfacing the ambiguity and avoid presenting the ambiguity as “resolved.”

## Visual findings
The current visual system is strong enough to preserve. No global redesign was made. The Behind the Lab letter surface + side support rail remains. The remaining visual QA should be screenshot-driven at desktop + laptop + mobile widths because composition cannot be proven by source inspection.

## Validation
- Full deterministic / regression suite: 656 / 656 passing after this round
- Python compileall: passing
- Analytics Python modules changed: 0
- New loop-contract tests cover stale-state guards, cross-lab handoffs, directory routing, MMM period/currency semantics, and the letter layout contract
