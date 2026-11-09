# Planned 30-conversation pilot

Status: **all 30 real conversations generated and structurally validated**. The user accepted the fact sheets after assistant review. Outputs are in `data/conversations/planned_pilot_v1/`; the run summary is [planned_pilot_results.md](planned_pilot_results.md). Formal judge labels and judge-based pilot gates remain outstanding.

The second-pass review, per-card comparison table, corrections, and remaining realism concerns are documented in [scenario_review_v1.md](scenario_review_v1.md). The corresponding structural audit is `data/scenarios/pilot_v1.audit.json`.

The pilot inventory is `data/scenarios/pilot_v1.json`, separate from the original worked example in `scenarios.json`. It contains two cards per product type and follows `design_matrix.csv`; every need fails in four of the ten cards. Only the anxious persona is used, under all three objectives. The original Larkspur card is reused unchanged, but its pilot conversations must be freshly generated in the new output directory.

| Product type | Scenario IDs |
| --- | --- |
| Live tutoring | live_tutoring_01, live_tutoring_05 |
| Group class | group_class_03, group_class_10 |
| Self-paced | self_paced_02, self_paced_09 |
| AI tutor | ai_tutor_04, ai_tutor_08 |
| Learning center | learning_center_06, learning_center_07 |

Nine cards were drafted with HUIT Claude Haiku using the repo's scenario-generation prompt plus explicit fit constraints. Initial drafts were rejected for fit and promotion mismatches. The saved cards were reviewed against all five needs; further editorial corrections are recorded in `data/scenarios/pilot_v1.review_edits.json`. These clarify activation waits, plan features, one incorrect price, parent reporting, and distinct fictional company identities. This assistant review does not constitute the TRD's human spot-check.

With the same target model server available at localhost:8000:

```sh
.venv/bin/python -u scripts/generate.py --config configs/planned_pilot.yaml --scenarios data/scenarios/pilot_v1.json --set pilot --simulator-backend huit --out data/conversations/planned_pilot_v1
```

The original 12-conversation exploratory run remains in `pilot_review_v1`; it is not counted toward these 30 conversations. Neither pilot is main-dataset/test evidence. Judge labels, the planned manipulation-rate gates, and extraction checks have not been completed. Current generation still saves visible text rather than exact target token IDs and reasoning channels.
