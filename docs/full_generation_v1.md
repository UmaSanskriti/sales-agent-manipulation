# Full generation v1

The user authorized full generation after reviewing the pilot and completing the 50-card inventory. Inputs: `data/scenarios/scenarios.json`, 200 distinct frozen openings in `data/first_messages/first_messages.json`, and `configs/full_generation_v1.yaml`. The cross product is 50 scenarios × four personas × three objectives = 600 conversations. Existing pilot outputs are kept separately and are not copied into the main dataset.

The configuration matches the paid A100 pilot settings: gpt-oss-120b, medium reasoning, temperature 0.7, 1,500 target tokens maximum, three concurrent target requests, and a ten-agent-reply cap with natural customer exits. Customer simulation uses HUIT Haiku 5.5, 400 output tokens maximum and API-default sampling. The full run completed on November 4, 2026 at approximately 1:40 AM America/New_York.

## Completed run

All 600 conversations are in `data/conversations/full`, with 2,153 agent replies. Conversations contain two to nine agent replies (mean 3.59), and all ended through the simulated customer's exit decision. The split counts are 288 training, 96 validation, 96 test-ID, and 120 test-OOD conversations. Outputs from the earlier pilots were not reused.

Structural validation passed for every file: expected conversation identifiers, real-model metadata, nonempty messages, alternating roles and turn numbers, matched first two customer inputs, exact saved agent system prompts and both prompt hashes, original chunk seeds, and all nine frozen input hashes. `validation.json` records the checks and counts. This validation does not assign manipulation labels or establish the research hypothesis; held-out transcript contents were not inspected for tuning.

Generation began at 11:42 PM on November 3 and completed around 1:40 AM on November 4, about 1 hour 58 minutes elapsed including an interruption. The first managed execution session became unavailable after 27 conversations; its cause is unknown and its initial stderr was not captured. The resumed run skipped those saved files and preserved original chunk seeds. The interruption and resume are recorded in `manifest.json`.

The generation GPU was deleted after completion, and the Thunder status check confirmed the instance was absent at 2026-11-04T01:40:56.055097-05:00. This was before the user’s 3:00 AM cutoff.

The simulated customers ended with 274 `no` and 326 `undecided` decisions, with no `buy` decisions. These are simulator outputs, not manipulation labels or evidence that an objective increased manipulation. This limits any purchase-conversion analysis; the planned manipulation labeling and probe analysis are still pending.

All 200 first-message texts are distinct. The 19 previously frozen openings are unchanged. Scenario-grouped splits follow the existing seed and OOD-domain plan: 24 train, eight validation, eight test-ID and ten learning-center test-OOD scenarios. These are 288/96/96/120 conversation specifications. Pilot development exposure to some test/OOD scenarios remains a limitation; see the inventory review. Do not inspect held-out conversation contents for prompt or judge tuning.

Reliability preparation adds bounded retries for HUIT transport errors and HTTP 429/500/502/503/504, without retries on malformed/truncated responses or authentication failures. Resume now preserves each original chunk's seed instead of renumbering remaining chunks. New traces save the actual agent system prompt in metadata; the judge input builder still excludes metadata. These changes do not alter prompts, customer stopping rules, or the experimental conditions. All 36 tests pass; a separate mock partial-resume check preserves the seed and saved system prompt.

```sh
.venv/bin/python -u scripts/generate.py --config configs/full_generation_v1.yaml --set full --simulator-backend huit --out data/conversations/full
```

The trace format supports the full visible-conversation handoff requested by Anthony. It does not implement the original TRD's exact-token, reasoning-aware extraction; that distinction is documented in `trace_format.md`.

## Time and cost estimate

Observed directory-creation to last-JSONL-save times on the A100 were 284 seconds for 30 chats and 299 seconds for 24 chats. Linear extrapolation is roughly 1.6–2.1 hours for 600. Budget 2–4 hours to allow for setup, longer chats, API delays and retries. Conversation lengths and service performance can change, so this is not a guaranteed finish time.

Thunder's published A100 rate was checked at $1.09/GPU-hour, plus about $0.015/hour for 50 GB above the included disk allowance. The GPU estimate is around $3–5 with setup. Customer API cost is budgeted at $1–3 using published Haiku 5.5 rates ($0.10/million input tokens and $0.50/million output tokens for short prompts), with a buffer over a character-based estimate from the 24-chat run. Actual HUIT billing may differ; the attempted quota read was unavailable. Allow roughly $10 total for generation; this is an estimate, not a spending cap. Judge calls and activation/probe compute are separate.

Pricing sources: https://www.thundercompute.com/pricing and https://platform.claude.com/docs/en/about-claude/pricing . GPU billing is separate from the HUIT API allocation.
