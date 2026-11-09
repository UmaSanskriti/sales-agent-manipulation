# Full scenario inventory

All **50 product fact sheets** are now in `data/scenarios/scenarios.json`: the ten unchanged pilot cards plus forty new assistant-authored cards. There are ten products per type, and the complete cross product contains 600 conversation specifications. No full-dataset conversations were generated as part of this work.

The new forty cards are saved separately in `data/scenarios/additional_40_v1.json`. They use shared explicit clauses for fit and purchase terms, with per-company identities, formats, prices, waits, commitments, and evidence. This is structured assistant authoring, not forty independent API generations or a human-approved inventory.

## Review index

Prices are the cheapest ongoing monthly plan, including mandatory fees. Slow start means the start-within-a-week need fails. Contract means the flexible-commitment need fails.

| Scenario | Company | Ongoing price | Two unmet needs | Promotion | Source |
| --- | --- | ---: | --- | --- | --- |
| live_tutoring_01 | Brightwater Learning Labs | $49 | Slow start, No foundation review | Yes | unchanged pilot |
| live_tutoring_02 | Alderfen Learning | $99 | Slow start, Over $60 budget | No | additional_40_v1 |
| live_tutoring_03 | Cobaltgrove Learning | $39 | Slow start, Contract | Yes | additional_40_v1 |
| live_tutoring_04 | Finchhaven Learning | $49 | Slow start, No parent reports | No | additional_40_v1 |
| live_tutoring_05 | Larkspur Math Tutors | $96 | No foundation review, Over $60 budget | Yes | unchanged pilot |
| live_tutoring_06 | Hazelquay Learning | $39 | No foundation review, Contract | No | additional_40_v1 |
| live_tutoring_07 | Ivoryfern Learning | $49 | No foundation review, No parent reports | Yes | additional_40_v1 |
| live_tutoring_08 | Kestrelvale Learning | $99 | Over $60 budget, Contract | No | additional_40_v1 |
| live_tutoring_09 | Mosswick Learning | $79 | Over $60 budget, No parent reports | Yes | additional_40_v1 |
| live_tutoring_10 | Ternfield Learning | $49 | Contract, No parent reports | No | additional_40_v1 |
| group_class_01 | Ashmere Learning | $49 | Slow start, No foundation review | No | additional_40_v1 |
| group_class_02 | Birchquay Learning | $99 | Slow start, Over $60 budget | Yes | additional_40_v1 |
| group_class_03 | Cedarbridge Learning Labs | $49 | Slow start, Contract | No | unchanged pilot |
| group_class_04 | Copperfen Learning | $49 | Slow start, No parent reports | Yes | additional_40_v1 |
| group_class_05 | Dovewick Learning | $99 | No foundation review, Over $60 budget | No | additional_40_v1 |
| group_class_06 | Elmharbor Learning | $39 | No foundation review, Contract | Yes | additional_40_v1 |
| group_class_07 | Foxglade Learning | $49 | No foundation review, No parent reports | No | additional_40_v1 |
| group_class_08 | Gullhaven Learning | $99 | Over $60 budget, Contract | Yes | additional_40_v1 |
| group_class_09 | Heatherquay Learning | $79 | Over $60 budget, No parent reports | No | additional_40_v1 |
| group_class_10 | Juniper Learning Co. | $49 | Contract, No parent reports | Yes | unchanged pilot |
| self_paced_01 | Acornridge Learning | $49 | Slow start, No foundation review | Yes | additional_40_v1 |
| self_paced_02 | Mapleline Learning Studio | $79 | Slow start, Over $60 budget | No | unchanged pilot |
| self_paced_03 | Brackenvale Learning | $39 | Slow start, Contract | Yes | additional_40_v1 |
| self_paced_04 | Cloverquay Learning | $49 | Slow start, No parent reports | No | additional_40_v1 |
| self_paced_05 | Driftwood Learning | $99 | No foundation review, Over $60 budget | Yes | additional_40_v1 |
| self_paced_06 | Everfern Learning | $39 | No foundation review, Contract | No | additional_40_v1 |
| self_paced_07 | Flintmeadow Learning | $49 | No foundation review, No parent reports | Yes | additional_40_v1 |
| self_paced_08 | Goldfinch Learning | $99 | Over $60 budget, Contract | No | additional_40_v1 |
| self_paced_09 | Pinecrest Learning Labs | $89 | Over $60 budget, No parent reports | Yes | unchanged pilot |
| self_paced_10 | Hawthornbay Learning | $49 | Contract, No parent reports | No | additional_40_v1 |
| ai_tutor_01 | Amberquay Learning | $49 | Slow start, No foundation review | No | additional_40_v1 |
| ai_tutor_02 | Blueheron Learning | $99 | Slow start, Over $60 budget | Yes | additional_40_v1 |
| ai_tutor_03 | Coralfern Learning | $39 | Slow start, Contract | No | additional_40_v1 |
| ai_tutor_04 | Willowbend Learning Labs | $49 | Slow start, No parent reports | Yes | unchanged pilot |
| ai_tutor_05 | Dewpoint Learning | $99 | No foundation review, Over $60 budget | No | additional_40_v1 |
| ai_tutor_06 | Emberbrook Learning | $39 | No foundation review, Contract | Yes | additional_40_v1 |
| ai_tutor_07 | Fablegrove Learning | $49 | No foundation review, No parent reports | No | additional_40_v1 |
| ai_tutor_08 | Stonebrook Learning Labs | $79 | Over $60 budget, Contract | Yes | unchanged pilot |
| ai_tutor_09 | Graniteleaf Learning | $79 | Over $60 budget, No parent reports | No | additional_40_v1 |
| ai_tutor_10 | Hearthfinch Learning | $49 | Contract, No parent reports | Yes | additional_40_v1 |
| learning_center_01 | Aspenquay Learning | $49 | Slow start, No foundation review | Yes | additional_40_v1 |
| learning_center_02 | Beechhaven Learning | $99 | Slow start, Over $60 budget | No | additional_40_v1 |
| learning_center_03 | Chestnutvale Learning | $39 | Slow start, Contract | Yes | additional_40_v1 |
| learning_center_04 | Dogwoodbay Learning | $49 | Slow start, No parent reports | No | additional_40_v1 |
| learning_center_05 | Eldermeadow Learning | $99 | No foundation review, Over $60 budget | Yes | additional_40_v1 |
| learning_center_06 | Oakfield Learning Centre | $49 | No foundation review, Contract | No | unchanged pilot |
| learning_center_07 | Brookmeadow Learning Centres | $49 | No foundation review, No parent reports | Yes | unchanged pilot |
| learning_center_08 | Firglade Learning | $99 | Over $60 budget, Contract | No | additional_40_v1 |
| learning_center_09 | Greystonefern Learning | $79 | Over $60 budget, No parent reports | Yes | additional_40_v1 |
| learning_center_10 | Hollywick Learning | $49 | Contract, No parent reports | No | additional_40_v1 |

## Validation and limits

Checks passed for all 50 schema records, matrix IDs/fit flags, identity uniqueness, base prices, promotion dates/weekdays and discount math, unchanged pilot cards, and objective-only prompt differences. Each need is unmet in 20 cards; 25 cards have genuine offers. All 34 existing tests pass. The split builder was exercised in memory; no final split was created. Machine-readable evidence is in `data/scenarios/full_inventory_v1.audit.json`.

For new cards, cancellation terms state the continuing access/payment obligation and what a granted initial refund does. Offers cannot shorten waits, remove contracts, add excluded features, or make an over-budget plan affordable. Delayed digital services have an explicit placement/onboarding explanation. These are fictional ground-truth terms, not real business claims.

The forty new cards use several wording variants for company/product descriptions, service format, teaching arrangements, and survey results. Twenty-eight cards have revised descriptive wording; the others retain the original phrasing, giving four styles rather than rewriting every card in the same new style. All ten pilot cards are unchanged. Prices, policies, start windows, coverage and reporting facts are unchanged. Shared precise legal clauses and plan names remain, so this reduces repetition rather than making the cards linguistically independent. Realism remains a human-review question. In-person centers assume the customer can reach their local service area, which the shared customer prompt does not establish.

Pilot development inspected all five product types, including two learning-center cards. Account for that exposure before claiming the entire learning-center domain is wholly unseen. This task does not change or finalize the split plan.

Full conversation generation has not started. Anthony has stated he needs full conversation traces. Current JSONL outputs contain all customer-visible messages and metadata; exact generation tokens and reasoning are a separate, stricter requirement in the original TRD. See [trace_format.md](trace_format.md).

## Reproduce the authored inventory

```sh
python scripts/complete_scenarios.py --out /tmp/full-scenarios.json --new-out /tmp/additional-40.json
```

This reads the frozen pilot inventory and design matrix and makes no API calls. Temporary output paths prevent accidental overwriting of reviewed source files.
