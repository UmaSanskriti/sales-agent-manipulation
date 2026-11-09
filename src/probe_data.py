"""Join judge labels, splits, reply text and stored activations into probe datasets.

Target: harm = (judge harm_tier > 0), i.e. tiers 1-4 pooled against tier 0. The 31 train turns
with a tactic but sales_attempt = false stay harm = 1.

Two granularities:
  turn   one row per judged agent turn
  conv   one row per conversation; label = any judged turn is harm
         conv_final: the final agent turn's vector (it has seen the whole conversation)
         conv_mean:  mean of every judged turn's vector
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.acts import POSITIONS

ROOT = Path(__file__).resolve().parent.parent
LABELS_TRAINVAL = ROOT / "data" / "labels" / "judge_v3.jsonl"
LABELS_TEST = ROOT / "data" / "labels" / "judge_v3_test.jsonl"
SPLITS = ROOT / "data" / "splits" / "splits.json"
CONV_DIR = ROOT / "data" / "conversations" / "full"
ACT_DIR = ROOT / "data" / "activations"
SPLIT_NAMES = ("train", "val", "test", "test_ood")


def load_splits(path: Path = SPLITS) -> dict[str, str]:
    return json.loads(Path(path).read_text())


def scenario_of(conv_id: str) -> str:
    return conv_id.rsplit("__", 2)[0]


def load_labels(include_test: bool = False) -> list[dict]:
    """Judge labels with harm and the conversation's condition. Test labels load only on request,
    so only the final evaluation script touches them."""
    paths = [LABELS_TRAINVAL] + ([LABELS_TEST] if include_test else [])
    rows = []
    for p in paths:
        for line in Path(p).read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                r["harm"] = int(r["harm_tier"] > 0)
                r["scenario_id"] = scenario_of(r["conv_id"])
                r["condition"] = r["conv_id"].rsplit("__", 1)[1]
                rows.append(r)
    return rows


def all_labeled_turn_ids() -> list[str]:
    """Row order of the activation array: every judged turn (all splits), sorted. Reads only ids."""
    ids = []
    for p in (LABELS_TRAINVAL, LABELS_TEST):
        ids += [json.loads(l)["turn_id"] for l in Path(p).read_text().splitlines() if l.strip()]
    return sorted(ids)


def load_reply_texts(conv_dir: Path = CONV_DIR) -> dict[str, str]:
    """{turn_id: agent reply text} from the conversation files."""
    out = {}
    for p in sorted(Path(conv_dir).glob("*.jsonl")):
        recs = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
        cid = recs[0]["conv_id"]
        for r in recs[1:]:
            if r["role"] == "agent":
                out[f"{cid}#t{r['turn']}"] = r["content"]
    return out


@dataclass
class Rows:
    ids: list[str]            # turn_id or conv_id
    y: np.ndarray
    scenario: np.ndarray
    condition: np.ndarray
    split: np.ndarray
    act_rows: list[list[int]]  # activation row(s) behind each example (1 for turns, >=1 for convs)
    text: list[str]            # reply text (turns) or concatenated replies (convs)

    def mask(self, split: str) -> np.ndarray:
        return self.split == split


def build_rows(level: str, labels: list[dict], row_of: dict[str, int], splits: dict[str, str],
               texts: dict[str, str] | None = None) -> Rows:
    """level: 'turn' or 'conv'. Examples whose activations are missing are skipped."""
    texts = texts or {}
    labels = [r for r in labels if r["turn_id"] in row_of]
    if level == "turn":
        ex = [(r["turn_id"], [r], ) for r in labels]
    else:
        by: dict[str, list[dict]] = {}
        for r in labels:
            by.setdefault(r["conv_id"], []).append(r)
        ex = [(cid, sorted(rs, key=lambda r: r["turn"])) for cid, rs in sorted(by.items())]
    ids, y, scen, cond, spl, rows, txt = [], [], [], [], [], [], []
    for key, rs in ex:
        ids.append(key)
        y.append(int(any(r["harm"] for r in rs)))
        scen.append(rs[0]["scenario_id"])
        cond.append(rs[0]["condition"])
        spl.append(splits[rs[0]["scenario_id"]])
        rows.append([row_of[r["turn_id"]] for r in rs])
        txt.append("\n".join(texts.get(r["turn_id"], "") for r in rs))
    return Rows(ids, np.array(y), np.array(scen), np.array(cond), np.array(spl), rows, txt)


def features(acts, rows: Rows, mask: np.ndarray, layer: int, position: str, agg: str = "final") -> np.ndarray:
    """[n, D] float32 activations for the examples in `mask`. agg applies to conversations only:
    'final' = last judged turn, 'mean' = mean over judged turns."""
    p = POSITIONS.index(position)
    out = []
    for i in np.flatnonzero(mask):
        r = rows.act_rows[i]
        if len(r) == 1:
            out.append(acts[r[0], layer, p])
        elif agg == "final":
            out.append(acts[r[-1], layer, p])
        else:
            out.append(np.asarray(acts[r, layer, p], dtype=np.float32).mean(0))
    return np.asarray(out, dtype=np.float32)


def check_counts(rows: Rows, min_count: int = 15) -> list[str]:
    """TRD M6 rule: stop and report if a split has too few examples of either class."""
    problems = []
    for s in SPLIT_NAMES:
        m = rows.mask(s)
        if not m.any():
            continue
        pos, neg = int(rows.y[m].sum()), int((1 - rows.y[m]).sum())
        if pos < min_count or neg < min_count:
            problems.append(f"{s}: {pos} harm / {neg} not harm")
    return problems
