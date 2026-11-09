"""Token positions, row alignment and probe plumbing, with a fake harmony-style tokenizer."""
import re

import numpy as np
import pytest

from src.acts import FINAL_MARKER, agent_turn_indices, locate_turns, to_chat
from src.probe_data import all_labeled_turn_ids, build_rows, check_counts, features, load_labels
from src.probes import best_threshold, bootstrap_by_group, make_probe, metrics
from src.schema import Message

SPECIAL = r"(<\|[a-z]+\|>)"


class FakeTok:
    def apply_chat_template(self, chat, add_generation_prompt=False, tokenize=False, reasoning_effort=None):
        t = ""
        for m in chat:
            if m["role"] == "system":
                t += f"<|start|>system<|message|>{m['content']}<|end|>"
            elif m["role"] == "user":
                t += f"<|start|>user<|message|>{m['content']}<|end|>"
            else:
                t += f"<|start|>assistant{FINAL_MARKER}{m['content']}<|end|>"
        return t + ("<|start|>assistant" if add_generation_prompt else "")

    def __call__(self, text, add_special_tokens=False):
        toks = [x for x in re.split(SPECIAL, text) if x]
        ids = []
        for x in toks:
            ids += [x] if re.fullmatch(SPECIAL, x) else x.split()
        return {"input_ids": ids}


MSGS = [Message("customer", "hello there", 1), Message("agent", "hi I am Dana", 1),
        Message("customer", "price please", 2), Message("agent", "It is cheap today", 2),
        Message("customer", "bye now", 3)]


def test_positions_point_at_the_expected_tokens():
    ids, spans = locate_turns(FakeTok(), "sys", MSGS)
    assert [s["turn"] for s in spans] == [1, 2]
    for s, text in zip(spans, ("hi I am Dana", "It is cheap today")):
        assert ids[s["pre"]] == "assistant"
        assert ids[s["start"]:s["end"]] == text.split()
        assert ids[s["start"] - 1] == "<|message|>"
    assert "bye" not in ids  # the closing customer remark is dropped


def test_empty_agent_turns_are_skipped_like_the_judge():
    msgs = [Message("customer", "a", 1), Message("agent", "  ", 1), Message("customer", "b", 2),
            Message("agent", "ok then", 2)]
    assert agent_turn_indices(msgs) == [3]
    ids, spans = locate_turns(FakeTok(), "sys", msgs)
    assert [s["turn"] for s in spans] == [2]
    assert [m["role"] for m in to_chat("sys", msgs)] == ["system", "user", "user", "assistant"]


def test_broken_prefix_raises():
    class Bad(FakeTok):
        def __call__(self, text, add_special_tokens=False):
            out = super().__call__(text)
            if text.endswith("<|end|>") and "<|message|>It is" in text:  # full text tokenizes differently
                out["input_ids"] = ["different"] + out["input_ids"][1:]
            return out
    with pytest.raises(ValueError):
        locate_turns(Bad(), "sys", MSGS)


def test_labels_and_row_order_cover_every_judged_turn():
    trainval = load_labels()
    ids = all_labeled_turn_ids()
    assert len(ids) == len(set(ids)) == 2150 and ids == sorted(ids)
    assert not any(r["scenario_id"] is None for r in trainval)
    assert {r["harm"] for r in trainval} == {0, 1}
    assert len(trainval) == 1372  # test labels are not loaded unless asked for


def test_conv_rows_label_any_harm_and_features_pick_the_right_turn():
    labels = [{"turn_id": f"s_a_neutral#t{t}", "conv_id": "s_a_neutral", "turn": t, "harm": h,
               "scenario_id": "s", "condition": "neutral"} for t, h in ((1, 0), (2, 1), (3, 0))]
    acts = np.zeros((3, 2, 3, 4), dtype=np.float16)
    for i in range(3):
        acts[i, 1, 1] = i + 1
    rows = {l["turn_id"]: i for i, l in enumerate(labels)}
    conv = build_rows("conv", labels, rows, {"s": "train"})
    assert conv.y.tolist() == [1] and conv.act_rows == [[0, 1, 2]]
    m = conv.mask("train")
    assert features(acts, conv, m, 1, "last", "final")[0, 0] == 3
    assert features(acts, conv, m, 1, "last", "mean")[0, 0] == 2
    assert check_counts(conv)  # far too few examples: the TRD stop rule fires


def test_metrics_and_probe_plumbing():
    rng = np.random.default_rng(0)
    y = np.array([0, 1] * 40)
    X = rng.normal(size=(80, 6)) + 2 * y[:, None]
    for kind, hp in (("lr", 1.0), ("mlp", 1.0)):
        p = make_probe(kind, hp).fit(X, y).predict_proba(X)[:, 1]
        thr = best_threshold(y, p)
        m = metrics(y, p, thr)
        assert m["auroc"] > 0.9 and sum(map(sum, m["confusion"])) == 80
        assert 0 <= m["recall"]["harm"] <= 1
    ci = bootstrap_by_group(y, p, thr, np.arange(80) % 8, n=50)
    assert ci["auroc_ci"][0] <= ci["auroc_ci"][1]
