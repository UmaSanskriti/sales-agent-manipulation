"""Render judge labels next to their transcripts as Markdown, for human review.

    python scripts/judge_review.py                      # data/labels/judge_v1.jsonl -> data/labels/judge_v1_review.md
    python scripts/judge_review.py --blind              # hide condition and labels (sheet for hand-labeling)
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from prompts.prompts import JUDGE_RUBRIC_VERSION, render_facts_block  # noqa: E402
from src.judge.inputs import load_conversation  # noqa: E402
from src.scenarios import load_scenarios  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default=str(ROOT / "data" / "labels" / f"judge_{JUDGE_RUBRIC_VERSION}.jsonl"))
    ap.add_argument("--conv-dir", default=str(ROOT / "data" / "conversations" / "full"))
    ap.add_argument("--out")
    ap.add_argument("--blind", action="store_true", help="omit condition and judge labels")
    args = ap.parse_args()
    labels_path = Path(args.labels)
    out = Path(args.out) if args.out else labels_path.with_name(labels_path.stem + ("_blind" if args.blind else "_review") + ".md")

    by_conv = defaultdict(dict)
    for line in labels_path.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            if r.get("rubric") == JUDGE_RUBRIC_VERSION:
                by_conv[r["conv_id"]][r["turn"]] = r
    scenarios = {s.id: s for s in load_scenarios()}

    lines = [f"# Judge {JUDGE_RUBRIC_VERSION} labels: {len(by_conv)} conversations\n"]
    for conv_id in sorted(by_conv, key=lambda c: (c.split("__")[0], c.split("__")[1], c.split("__")[2])):
        spec, messages, meta = load_conversation(Path(args.conv_dir) / f"{conv_id}.jsonl")
        title = f"{spec.scenario_id} / {spec.persona_id}" + ("" if args.blind else f" / **{spec.condition}**")
        lines.append(f"\n---\n\n## {title}\n")
        if not args.blind:
            lines.append(f"Customer decision: {meta.get('decision')}\n")
        lines.append("<details><summary>Company materials</summary>\n\n```\n" + render_facts_block(scenarios[spec.scenario_id]) + "\n```\n</details>\n")
        for m in messages:
            if m.role == "customer":
                lines.append(f"\n**Customer (turn {m.turn}):** {m.content}\n")
                continue
            lines.append(f"\n**Agent (turn {m.turn}):** {m.content}\n")
            r = by_conv[conv_id].get(m.turn)
            if args.blind or r is None:
                lines.append("\n> sales_attempt: ____  tactics (A-F): ____  notes: ____\n" if args.blind else "\n> (not judged)\n")
                continue
            verdict = f"MANIPULATIVE (harm tier {r['harm_tier']})" if r["manipulative"] else "clean"
            conf = {t: v for t, v in r["confidence"].items() if v}
            lines.append(f"\n> **{verdict}** sales_attempt={r['sales_attempt']} confidence={conf or '-'}")
            for e in r["evidence"]:
                lines.append(f">\n> - **[{e['tactic']}]** quote: \"{e['quote']}\"\n>   basis: \"{e['basis']}\"\n>   why: {e['why']}")
            if r["ledger"]:
                lines.append(">\n> <details><summary>ledger (" + ", ".join(f"{v}: {sum(c['verdict'] == v for c in r['ledger'])}" for v in ("supported", "unsupported", "contradicted")) + ")</summary>\n>")
                lines += [f"> - {c['verdict']}: {c['claim']}" for c in r["ledger"]]
                lines.append(">\n> </details>")
            lines.append("")
    out.write_text("\n".join(lines))
    print(f"wrote {out} ({len(by_conv)} conversations)")


if __name__ == "__main__":
    main()
