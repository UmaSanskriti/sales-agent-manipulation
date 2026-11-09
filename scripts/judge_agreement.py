"""Human-judge agreement on the blind sample (TRD M5 validation).

    python scripts/judge_agreement.py data/labels/human/labels_alice.csv data/labels/human/labels_bob.csv

Each CSV has columns id, sales_attempt (0/1), tactics (letters A-F, empty = none), notes.
Reports Cohen's kappa for manipulative (any tactic) and sales_attempt, human-human and
human-judge, per-tactic agreement, and judge agreement by its confidence.
"""
import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from prompts.prompts import JUDGE_RUBRIC_VERSION, TACTICS  # noqa: E402


def kappa(a: list, b: list) -> float:
    """Cohen's kappa for two equal-length lists of labels."""
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(a) | set(b)) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def read_human(path: Path) -> dict:
    out = {}
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            tactics = sorted({c for c in row["tactics"].upper() if c in TACTICS})
            out[row["id"]] = {"sales_attempt": row["sales_attempt"].strip() == "1", "tactics": tactics,
                              "manipulative": bool(tactics)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csvs", nargs="+", help="one labels CSV per annotator")
    ap.add_argument("--key", default=str(ROOT / "data" / "labels" / "human" / f"sample_{JUDGE_RUBRIC_VERSION}.key.json"))
    ap.add_argument("--labels", nargs="+", default=[str(ROOT / "data" / "labels" / f"judge_{JUDGE_RUBRIC_VERSION}.jsonl")])
    args = ap.parse_args()

    key = json.loads(Path(args.key).read_text())
    judge = {}
    for p in args.labels:
        for line in Path(p).read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                judge[r["turn_id"]] = r
    humans = {Path(p).stem.replace("labels_", ""): read_human(Path(p)) for p in args.csvs}
    ids = [h for h in key if all(h in hv for hv in humans.values()) and key[h]["turn_id"] in judge]
    print(f"{len(ids)} items with all labels (sample {len(key)}, judge rows {len(judge)})")
    J = {h: judge[key[h]["turn_id"]] for h in ids}

    for field in ("manipulative", "sales_attempt"):
        print(f"\n== {field}: kappa")
        names = list(humans)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                print(f"  {names[i]} vs {names[j]}: {kappa([humans[names[i]][h][field] for h in ids], [humans[names[j]][h][field] for h in ids]):.2f}")
        for n in names:
            print(f"  {n} vs judge: {kappa([humans[n][h][field] for h in ids], [J[h][field] for h in ids]):.2f}")
        if len(names) >= 2:
            maj = [sum(humans[n][h][field] for n in names) * 2 > len(names) for h in ids]
            print(f"  human majority vs judge: {kappa(maj, [J[h][field] for h in ids]):.2f}  "
                  f"(humans positive {sum(maj)}, judge positive {sum(J[h][field] for h in ids)})")

    print("\n== per-tactic agreement with the human majority (present/absent)")
    for t in TACTICS:
        hm = [sum(t in humans[n][h]["tactics"] for n in humans) * 2 > len(humans) for h in ids]
        jm = [t in J[h]["tactics"] for h in ids]
        both = sum(a and b for a, b in zip(hm, jm))
        print(f"  {t}: humans {sum(hm):2d}, judge {sum(jm):2d}, both {both:2d}, kappa {kappa(hm, jm):.2f}")

    print("\n== judge agreement with the human majority on 'manipulative', by judge confidence (max over tactics)")
    maj = {h: sum(humans[n][h]["manipulative"] for n in humans) * 2 > len(humans) for h in ids}
    by_conf = defaultdict(list)
    for h in ids:
        by_conf[max(J[h]["confidence"].values())].append(maj[h] == J[h]["manipulative"])
    for c in sorted(by_conf):
        v = by_conf[c]
        print(f"  confidence {c}: {sum(v)}/{len(v)} agree")

    print("\n== disagreements (human majority vs judge), by condition")
    dis = defaultdict(list)
    for h in ids:
        if maj[h] != J[h]["manipulative"]:
            dis[key[h]["condition"]].append(f"{h} humans={'yes' if maj[h] else 'no'} judge={J[h]['tactics'] or 'clean'}")
    for c, items in sorted(dis.items()):
        print(f"  {c}: " + "; ".join(items))


if __name__ == "__main__":
    main()
