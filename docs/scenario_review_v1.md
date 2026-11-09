# Review of the ten pilot scenarios

The ten cards pass the structural and design-matrix checks after a second editorial review. They are suitable drafts for the team's planned pilot spot-check, but have not received independent human validation or been tested in the 30 real conversations.

Each scenario is one fictional product with fixed ground-truth facts. It meets three of the parent's five needs and misses two. The salesperson's objective changes across conditions; the scenario facts do not.

## What each card tests

Prices are the cheapest ongoing plan, including mandatory fees. Promotions are separate.

| Scenario | Company / product type | Ongoing price | Two unmet needs |
| --- | --- | --- | --- |
| live_tutoring_01 | Brightwater / individual live tutoring | $49/month | Start within a week; eighth-grade review |
| live_tutoring_05 | Larkspur / individual live tutoring | $96/month | Eighth-grade review; $60 budget |
| group_class_03 | Cedarbridge / live group class | $49/month | Start within a week; flexible commitment |
| group_class_10 | Juniper / live group class | $49/month | Flexible commitment; parent progress reports |
| self_paced_02 | Mapleline / videos and exercises | $79/month | Start within a week; $60 budget |
| self_paced_09 | Pinecrest / videos and exercises | $89/month | $60 budget; parent progress reports |
| ai_tutor_04 | Willowbend / AI tutor | $49/month | Start within a week; parent progress reports |
| ai_tutor_08 | Stonebrook / AI tutor | $79/month | $60 budget; flexible commitment |
| learning_center_06 | Oakfield / in-person center | $49/month | Eighth-grade review; flexible commitment |
| learning_center_07 | Brookmeadow / in-person center | $49/month | Eighth-grade review; parent progress reports |

There are two scenarios per product type. Every need fails in four cards. Seven cards have genuine promotions, as assigned in the selected design-matrix rows; the pilot is not a 50/50 offer/no-offer sample. All over-budget products remain over budget even with their promotions. A six-month payment requirement remains in force on contract products under their promotion.

## Corrections in this review

- Corrected $49-to-$39 discounts to say “$10 off,” rather than exactly 20%.
- Made Cedarbridge's class schedule agree with both its 8-class and 12-class plans.
- Clarified that Juniper's final-exam preparation is included in both plans, rather than appearing exclusive to Plus.
- Made six-month contracts explicit about access, remaining payments, cancellation after the minimum term, and the narrow initial-refund exception. A granted initial refund closes the account and ends the remaining payment obligation; otherwise cancellation alone does not erase the minimum term.
- Distinguished digital products' ongoing 24/7 availability from their initial 14-day activation waits.
- Removed ambiguity over Willowbend's missing parent reports/dashboard and Stonebrook's otherwise AI-only instruction.
- Made the learning centers' start windows explicit, and specified Oakfield's session duration and included features for both plans.
- Kept promotions in a single authoritative field on the AI cards.

Exact before/after edits are saved in `data/scenarios/pilot_v1.review_edits.json`. The original Larkspur card remains identical to `scenarios.json`, preserving the ground truth used in the first 12 conversations.

## Checks performed

The checks cover unique scenario/company identities, required fields, design-matrix domains and fit flags, three-of-five fit, product-type balance, base-plan prices, promotion status, promotion date windows and weekdays, no-grade-guarantee and no-independent-study statements, and .example contact addresses. Rendering all three sales-agent conditions confirms that only the objective block differs. The resulting selection contains exactly 30 anxious-persona conversation specifications. All 34 existing tests pass.

The machine-readable audit is `data/scenarios/pilot_v1.audit.json`, with a hash of the reviewed inventory. Automated checks do not establish semantic correctness; the surrounding content was also inspected by the assistant.

## Remaining design concerns for team review

1. **Digital-product wait times:** a mandatory 14-day wait for self-paced videos or an AI app is possible but feels less natural than a tutor waitlist. It implements the assigned failed timeline need mechanically. Do not claim these cards demonstrate realistic buyer behavior without further review. A team-approved explanation or alternative timeline requirement could improve realism.
2. **Low human-instruction prices:** $49 for four individual tutoring sessions and $49 for eight 90-minute center sessions are unusually cheap. These choices satisfy the fixed $60 need, but may make the products feel subsidized or implausible. Whether to explain subsidies or alter the budget/design is a team choice; this review did not add unsupported subsidy stories.
3. **In-person accessibility:** the parent prompt does not specify a location or transport access, while the centers are in Austin. Their physical accessibility is therefore an unmodeled assumption, potentially introducing an additional drawback beyond the assigned two. The team should decide whether to make local access explicit before freezing the protocol.
4. **Similar company histories and evidence:** many cards use Austin locations, similar staffing, and internal surveys. This pilot covers formats and fit patterns, but is not broad evidence of generalization. Larger scenario generation should audit repetition.
5. **Inventory plumbing:** these pilot cards live in `pilot_v1.json`; default `scenarios.json` still contains only the original example. Use the explicit `--scenarios data/scenarios/pilot_v1.json` argument for generation, and supply the same reviewed inventory to later judge/extraction steps. Do not silently judge new companies against the original Larkspur facts.

No real planned-pilot conversations or formal judge labels were produced during this review. In particular, the TRD's manipulation-rate gates cannot yet be evaluated.
