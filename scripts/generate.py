"""Generate multi-turn conversations (pilot or full set), batched and resumable.

    python scripts/generate.py --set pilot --dry-run         # mock models
    python scripts/generate.py --set pilot                   # up to 30 conversations, real models
    python scripts/generate.py --set full                    # all 600
    python scripts/generate.py --set full --scenario live_tutoring_05 --persona anxious   # 3 conversations
    python scripts/generate.py --set pilot --simulator-backend claude_code   # use `claude -p`, no API key

Conversations are processed in chunks of target.batch_size; finished
conversations are written immediately, and existing files are skipped on re-run.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from src.build_specs import all_specs, pilot_specs  # noqa: E402
from src.first_messages import get_first_messages, key  # noqa: E402
from prompts.prompts import PERSONAS  # noqa: E402
from src.llm import AnthropicClient, ClaudeCodeClient, HFTarget, MockClient, VLLMTarget  # noqa: E402
from src.huit import HuitBedrockClient  # noqa: E402
from src.scenarios import load_scenarios  # noqa: E402
from src.simulate import run_batch  # noqa: E402


def build_target(tcfg):
    if tcfg["backend"] == "vllm":
        return VLLMTarget(tcfg["model"], base_url=tcfg["base_url"],
                          reasoning_effort=tcfg.get("reasoning_effort"), workers=tcfg["batch_size"])
    return HFTarget(tcfg["model"], reasoning_effort=tcfg.get("reasoning_effort"), batch_size=tcfg["batch_size"])


def build_simulator(cfg, backend):
    sim = cfg["simulator"]
    if backend == "huit":
        return HuitBedrockClient(sim["huit_model"], workers=sim["workers"],
                                 key_file=ROOT / ".env" if (ROOT / ".env").exists() else None)
    if backend == "claude_code":
        return ClaudeCodeClient(sim["claude_code_model"], workers=sim["claude_code_workers"])
    return AnthropicClient(sim["model"], workers=sim["workers"], disable_thinking=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "configs" / "experiment.yaml"))
    ap.add_argument("--set", choices=["pilot", "full"], default="pilot")
    ap.add_argument("--dry-run", action="store_true", help="mock models; writes to data/conversations/_dryrun")
    ap.add_argument("--simulator-backend", choices=["api", "claude_code", "huit"], help="override config")
    ap.add_argument("--scenario", help="only this scenario id")
    ap.add_argument("--scenarios", help="scenario JSON inventory (defaults to checked-in scenarios.json)")
    ap.add_argument("--persona", choices=sorted(PERSONAS), help="only this persona")
    ap.add_argument("--out")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text())
    scenarios = load_scenarios(args.scenarios) if args.scenarios else load_scenarios()
    by_id = {s.id: s for s in scenarios}
    specs = pilot_specs(scenarios, cfg["pilot_n"]) if args.set == "pilot" else all_specs(scenarios)
    if args.scenario:
        specs = [s for s in specs if s.scenario_id == args.scenario]
    if args.persona:
        specs = [s for s in specs if s.persona_id == args.persona]
    if not specs:
        ap.error("No conversations match these filters. Pilot uses the anxious persona; use --set full for other personas.")

    backend = args.simulator_backend or cfg["simulator"].get("backend", "api")
    if args.dry_run:
        target, simulator, backend = MockClient("agent"), MockClient("customer"), "mock"
        out = Path(args.out or ROOT / "data" / "conversations" / "_dryrun" / args.set)
        fm_path = ROOT / "data" / "first_messages" / f"{args.set}_first_messages_dryrun.json"
    else:
        target = build_target(cfg["target"])
        simulator = build_simulator(cfg, backend)
        out = Path(args.out or ROOT / "data" / "conversations" / args.set)
        fm_path = ROOT / "data" / "first_messages" / "first_messages.json"
    out.mkdir(parents=True, exist_ok=True)

    sim_kw = {"max_tokens": cfg["simulator"]["max_tokens"]}
    tgt_kw = {"temperature": cfg["target"]["temperature"], "max_tokens": cfg["target"]["max_new_tokens"]}
    meta = {"target_model": cfg["target"]["model"], "target_backend": cfg["target"]["backend"],
            "target_reasoning_effort": cfg["target"].get("reasoning_effort"),
            "target_temperature": cfg["target"]["temperature"], "simulator_backend": backend,
            "simulator_model": cfg["simulator"][{"claude_code": "claude_code_model", "huit": "huit_model"}.get(backend, "model")],
            "simulator_temperature": "api_default" if backend in ("api", "huit") else None,
            "dry_run": args.dry_run}

    todo = [s for s in specs if not (out / f"{s.conv_id}.jsonl").exists()]
    print(f"{len(specs)} specs, {len(specs) - len(todo)} already done, {len(todo)} to generate -> {out}")
    firsts = get_first_messages([(s.scenario_id, s.persona_id) for s in todo], by_id, simulator, fm_path)

    bs = cfg["target"]["batch_size"]
    # Keep the original chunk seed on resume, even when earlier files exist.
    written = 0
    for ci in range(0, len(specs), bs):
        chunk = [s for s in specs[ci:ci + bs] if not (out / f"{s.conv_id}.jsonl").exists()]
        if not chunk:
            continue
        items = [(s, by_id[s.scenario_id], firsts[key(s.scenario_id, s.persona_id)]) for s in chunk]
        convs = run_batch(items, target, simulator, n_turns=cfg["n_turns"], target_kwargs=tgt_kw,
                          simulator_kwargs=sim_kw, seed=cfg["seed"] + ci // bs, meta=meta)
        for conv in convs:
            (out / f"{conv.spec.conv_id}.jsonl").write_text(
                "\n".join(json.dumps(r) for r in conv.to_records()) + "\n")
        written += len(convs)
        print(f"chunk {ci // bs + 1}: wrote {len(convs)} conversations ({written}/{len(todo)} remaining at start)")


if __name__ == "__main__":
    main()
