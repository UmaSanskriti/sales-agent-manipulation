"""Label agent turns with the manipulation judge (resumable; the output file is the cache).

    python scripts/judge.py --dry-run                                   # mock judge, 5% sample
    python scripts/judge.py --backend claude_code --sample-frac 0.05    # 5% of train+val via `claude -p`
    python scripts/judge.py --backend api --sample-frac 1               # everything in train+val
    python scripts/judge.py --splits test,test_ood --sample-frac 1      # held-out, run once, after the freeze
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from prompts.prompts import JUDGE_RUBRIC_VERSION  # noqa: E402
from src.judge.run import MockJudge, build_items, judge_turns, load_done, select_conversations  # noqa: E402
from src.llm import AnthropicClient, ClaudeCodeClient  # noqa: E402
from src.scenarios import load_scenarios  # noqa: E402


def build_judge(cfg, backend):
    j = cfg["judge"]
    if backend == "mock":
        return MockJudge(), "mock"
    if backend == "claude_code":
        return ClaudeCodeClient(j["claude_code_model"], workers=j["claude_code_workers"], timeout=120), j["claude_code_model"]
    if backend == "huit":
        from src.huit import HuitBedrockClient
        return HuitBedrockClient(j["huit_model"], workers=j["workers"], thinking=True, timeout=300,
                                 key_file=ROOT / ".env" if (ROOT / ".env").exists() else None), j["huit_model"]
    return AnthropicClient(j["model"], workers=j["workers"]), j["model"]


def summarize(out_path: Path, conv_dir: Path):
    rows = [json.loads(l) for l in out_path.read_text().splitlines() if l.strip()]
    rows = [r for r in rows if r.get("rubric") == JUDGE_RUBRIC_VERSION]
    by_cond = defaultdict(list)
    for r in rows:
        by_cond[r["conv_id"].split("__")[2]].append(r)
    print(f"\n{len(rows)} labeled turns in {out_path} (rubric {JUDGE_RUBRIC_VERSION})")
    for c in sorted(by_cond):
        rs = by_cond[c]
        pos = sum(r["manipulative"] for r in rs)
        tactics = Counter(t for r in rs for t in r["tactics"])
        tiers = Counter(r["harm_tier"] for r in rs if r["manipulative"])
        convs = {r["conv_id"] for r in rs}
        decisions = Counter(json.loads((conv_dir / f"{cid}.jsonl").open().readline())["decision"] for cid in convs)
        print(f"  {c:10s} turns {len(rs):4d}  manipulative {pos:3d} ({pos / len(rs):.0%})  "
              f"sales attempts {sum(r['sales_attempt'] for r in rs):3d}  harm tiers {dict(sorted(tiers.items()))}  "
              f"tactics {dict(sorted(tactics.items()))}  decisions {dict(decisions)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "configs" / "experiment.yaml"))
    ap.add_argument("--conv-dir", default=str(ROOT / "data" / "conversations" / "full"))
    ap.add_argument("--out", help="default data/labels/judge_<rubric>.jsonl")
    ap.add_argument("--backend", choices=["claude_code", "api", "huit", "mock"])
    ap.add_argument("--splits", default="train,val", help="comma-separated splits to draw from")
    ap.add_argument("--sample-frac", type=float, default=0.05, help="fraction of the whole dataset, as matched (scenario, persona) triples")
    ap.add_argument("--seed", type=int, default=20261104)
    ap.add_argument("--dry-run", action="store_true", help="mock judge; writes to data/labels/_dryrun/")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text())
    backend = "mock" if args.dry_run else (args.backend or cfg["judge"].get("backend", "claude_code"))
    out = Path(args.out) if args.out else (
        ROOT / "data" / "labels" / ("_dryrun" if args.dry_run else "") / f"judge_{JUDGE_RUBRIC_VERSION}.jsonl")
    splits = json.loads((ROOT / "data" / "splits" / "splits.json").read_text())
    scenarios = {s.id: s for s in load_scenarios()}

    files = select_conversations(Path(args.conv_dir), splits, set(args.splits.split(",")), args.sample_frac, args.seed)
    done = load_done(out)
    items = build_items(files, scenarios, done)
    print(f"{len(files)} conversations selected from splits {args.splits}; "
          f"{len(items)} turns to judge ({len(done)} already labeled) -> {out}")
    client, model_name = build_judge(cfg, backend)
    judge_turns(items, client, out, model_name=model_name, backend=backend,
                chunk=cfg["judge"].get("chunk", 16), max_tokens=cfg["judge"].get("max_tokens", 4000))
    summarize(out, Path(args.conv_dir))


if __name__ == "__main__":
    main()
