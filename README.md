# Sales-Agent Manipulation

Harvard CS 2881r · Fall 2026 · Gardenia Liu, Anthony Shen and Sanskriti Uma

We built a simulated tutoring marketplace to test whether optimising for sign-ups encourages an AI agent to mislead customers. The experiment compares three objectives across 50 fictional products and four customer personas, then tests whether activation probes can detect manipulation.

The turn-level probe reached **0.866 AUROC** on held-out scenarios, versus **0.836** for a text baseline. These scores measure agreement with an LLM judge, whose labels over-flagged some replies in human review.

[Results](reports/probe_results.md) · [Experiment design](docs/TRD.md) · [Code](src/) · [Team and source](SOURCE.md)

<details>
<summary>Setup, experiments and full technical documentation</summary>

# Does a sales objective increase manipulation, and can probes predict it?

Assignment 2. Open-weight sales agent, three system-prompt
conditions (neutral / conversion / harmful "sell at all costs"), four customer
personas, 50 edtech scenarios, 10-turn conversations, LLM-judge labels,
then activation probes that predict the judge. The full plan is in
[`docs/TRD.md`](docs/TRD.md).

## Current generation status

The customer can now end after the two matched opening exchanges by buying,
declining, or leaving undecided. The ten-exchange setting is a cap. Customer
follow-ups return private JSON decisions; only their words reach the agent.
A closing customer remark is saved without generating another sales reply.
Malformed simulator JSON stops the batch with an error instead of entering the transcript.

`data/scenarios/scenarios.json` now contains all **50 complete product cards**:
ten unchanged pilot cards plus forty new cards, with ten products per type.
See [the review index](docs/full_scenario_inventory.md) for each company's price,
two unmet needs, and promotion status. The paid full run is complete:
**600 conversations and 2,153 agent replies** are in
[`data/conversations/full`](data/conversations/full). All 600 passed structural
validation against the frozen inputs. See [the run report](docs/full_generation_v1.md)
for settings, checks, and limitations. Manipulation labels and activation probes
remain separate work.

`--set pilot` selects ten scenarios across product lines and runs the anxious
persona under all three objectives (30 conversations). To reproduce the original
planned pilot selection, explicitly pass `--scenarios data/scenarios/pilot_v1.json`;
the expanded default inventory selects a different subset. The completed pilot
and its results are documented in [planned_pilot_results.md](docs/planned_pilot_results.md).
To filter one product/persona, use `--set full --scenario live_tutoring_05 --persona skeptic`.

Use a **new output directory** when testing this protocol; resuming skips existing
filenames and does not update old fixed-length transcripts. For a free plumbing
check across all four personas:

```
python scripts/generate.py --set full --scenario live_tutoring_05 --dry-run --out /tmp/sales-stopping-dryrun
```

These checks do not establish that real customer reasoning improved. Review a
small new real-model pilot for repeated misunderstandings (including refund
eligibility), natural exits, and the balance of manipulation labels.

The current clients save full customer-visible dialogue and metadata, but not
exact target token IDs or reasoning channels. Anthony has requested full
conversation traces; those can support a visible-text replay extraction protocol.
That differs from the original exact-token, reasoning-aware TRD M1/M8 protocol.
See [trace_format.md](docs/trace_format.md) for the handoff and distinction.
The per-turn judge and extraction implementation remain separate work.

## Layout
| Path | Purpose |
|---|---|
| `docs/TRD.md` | Technical requirements: every design decision and the schedule |
| `prompts/prompts.py` | Customer situation and needs, personas, objections, system prompts, SOP, simulator / first-message / scenario-generation / judge prompts |
| `configs/experiment.yaml` | Models, turns, temperatures, seeds, split ratios |
| `data/scenarios/` | Company materials per scenario (the judge's ground truth) and `design_matrix.csv` (which needs each product fails) |
| `data/first_messages/` | Frozen first customer messages per scenario x persona |
| `data/conversations/` | Generated conversations (JSONL: meta line + one line per message) |
| `data/labels/`, `data/activations/`, `data/splits/` | Judge labels, probe features, split assignments |
| `src/` | `schema`, `scenarios`, `first_messages`, `llm`, `simulate`, `build_specs`, `splits`, `judge/inputs` |
| `scripts/generate.py` | Generate the pilot (30) or full (600) conversations: batched, concurrent, resumable |
| `tests/` | Mocked-LLM tests (`fakes.py` builds a 50-scenario set from the first real one) |

## Quick start

The configured simulator uses Harvard's HUIT Bedrock gateway with Claude Haiku
5.5 (`us.anthropic.claude-haiku-5-5`). Put `HUIT_API_KEY` in the ignored local
`.env` file (restrict permissions to the owner), or set it in the environment.
The key is sent only to the fixed Harvard gateway; no direct Anthropic or
personal-key fallback is used. Default sampling is retained and thinking is
disabled for short customer replies. Metadata records the Bedrock model id.
Use `--simulator-backend api` for a direct Anthropic key instead.

The HUIT client rejects truncated/empty replies and HTTP errors. A 400-token
simulator budget allows room for the message and the private stopping decision.
The live connection was checked with a short Haiku reply; this does not verify
the salesperson GPU server or activation extraction.

```
pip install -r requirements.txt
pytest
python scripts/generate.py --set pilot --dry-run   # mock models, no API or GPU
python scripts/generate.py --set pilot             # configured HUIT credentials and a running target model server
python scripts/generate.py --set pilot --simulator-backend claude_code   # simulator via `claude -p`, no API key
python scripts/generate.py --set full              # all 600, resumable
```
The Claude Code backend uses your logged-in `claude` CLI. **It is not prompt-clean**: with plan
login the CLI injects its own preamble, your account email and environment details around
our system prompt (`--bare` would remove them but requires an API key). Use it for pilots only;
use the API backend for the real dataset and the judge. It cannot set max tokens.
Neither backend can set temperature for the Claude 5.5 models (non-default values are
rejected), so simulator and judge runs use default sampling. Record that in the report.

## Sample run (3 conversations, one persona, all three conditions)
The agent runs on a rented GPU via vLLM; the simulator runs here through your logged-in `claude` CLI.
1. RunPod: deploy a pod with **1x H100 80GB** (MXFP4 needs Hopper), Docker image `vllm/vllm-openai:latest`,
   container start command `--model openai/gpt-oss-120b`, expose HTTP port **8000**, 150 GB volume at `/root/.cache/huggingface`.
   Wait for the log line `Application startup complete` (model download is ~65 GB, 10-20 min).
2. Check it answers: `curl https://<pod-id>-8000.proxy.runpod.net/v1/models`.
3. Set `target.base_url` in `configs/experiment.yaml` to `https://<pod-id>-8000.proxy.runpod.net/v1`.
4. `python scripts/generate.py --set full --scenario live_tutoring_05 --persona anxious --simulator-backend claude_code --out data/conversations/sample`
5. Read the three transcripts in `data/conversations/sample/`, then **stop the pod**.

## Design notes
- One customer pain point for every conversation: a parent whose teen is failing Algebra II,
  with five needs. Personas differ only in style. Each of the 50 companies' products meets
  exactly three needs, so no product is a clear fit (TRD M2).
- `data/scenarios/scenarios.json` holds all 50 company cards aligned with
  `design_matrix.csv`. The frozen ten-card pilot inventory is in `pilot_v1.json`;
  the new forty cards and authoring provenance are in `additional_40_v1.json`
  and its generation manifest. The new cards are assistant-authored with shared
  explicit clauses; they have not received independent human validation.
- Customer messages 1 (first message) and 2 (persona objection) are fixed per (scenario, persona)
  and identical across conditions; the simulator writes the rest.
- The three agent prompts share one template and differ only in the objective block.
  The sales SOP is procedural and carries no honesty, closing or time instructions.
- The customer simulator never sees the condition.
- Splits are by scenario: four product lines split 6/2/2 each, and `learning_center` is held
  out entirely as `test_ood`. All 12 conversations of a scenario land in one split.

## Leakage rules
- **Judge blindness:** build judge prompts only via `src/judge/inputs.py::build_judge_prompt`
  (facts + numbered transcript). Never pass the spec, filename, metadata or decision.
- **Split before anything else:** run `scripts/make_splits.py` once (it refuses to overwrite).
  Split is by scenario, stratified by product line, so all 12 conversations of a scenario share a split.
- **Human-labelled 5%:** use `src.splits.human_label_sample`; it draws only from train/val.
  Freeze the judge prompt before touching test.
- **Probe preprocessing** (scaling, layer and C selection) is fit on train / chosen on val only.

## Known confounds (address in the report)
- **Condition shortcut:** activations at the *start* of the response already encode the system
  prompt, so a probe can predict the condition instead of manipulation. Report a condition-only
  baseline and probe performance *within* each condition.
- **Instruction vs behavior:** the harmful prompt names the tactics the judge rubric lists, so
  labels partly measure instruction-following. Report per-category rates and read examples.
- **Persona** is balanced across conditions and splits but can still be a shortcut; report
  performance per persona and on the held-out product line (the generalization check).
- Text baseline (TF-IDF) sees only the agent response, the probe sees the full prompt context.

</details>
