"""Train/val/test and judge-blindness leakage checks."""
import json
from collections import Counter

import pytest

from prompts.prompts import CONDITIONS, OBJECTIVES
from src.build_specs import all_specs
from src.judge.inputs import judge_turn_prompts, load_conversation
from src.llm import MockClient
from src.scenarios import load_scenarios
from src.schema import ConvSpec
from src.simulate import run_batch
from src.splits import human_label_sample, save_splits, split_scenarios
from tests.fakes import fake_scenarios


def test_split_is_by_scenario_stratified_with_held_out_line():
    scn = fake_scenarios()
    splits = split_scenarios(scn, ood_domain="learning_center")
    assert Counter(splits.values()) == {"train": 24, "val": 8, "test": 8, "test_ood": 10}
    for d in {s.domain for s in scn}:
        expected = {"test_ood": 10} if d == "learning_center" else {"train": 6, "val": 2, "test": 2}
        assert Counter(splits[s.id] for s in scn if s.domain == d) == expected
    specs = all_specs(scn)
    assert len(specs) == 600
    assert Counter(splits[x.scenario_id] for x in specs) == {"train": 288, "val": 96, "test": 96, "test_ood": 120}


def test_split_is_deterministic_and_frozen(tmp_path):
    scn = fake_scenarios()
    assert split_scenarios(scn, seed=0) == split_scenarios(scn, seed=0)
    p = tmp_path / "splits.json"
    save_splits(split_scenarios(scn), p)
    with pytest.raises(FileExistsError):
        save_splits(split_scenarios(scn, seed=1), p)


def test_human_label_sample_never_touches_test_and_is_balanced():
    scn = fake_scenarios()
    splits = split_scenarios(scn, ood_domain="learning_center")
    specs = all_specs(scn)
    sample = human_label_sample(specs, splits)
    assert len(sample) == 30
    assert all(splits[s.scenario_id] in ("train", "val") for s in sample)
    assert Counter(s.condition for s in sample) == {c: 10 for c in CONDITIONS}
    assert len({s.conv_id for s in sample}) == 30


def test_judge_input_boundary_is_condition_blind(tmp_path):
    s = load_scenarios()[0]
    spec = ConvSpec(s.id, "analytical", "harmful")
    conv = run_batch([(spec, s, "hi")], MockClient("a"), MockClient("c"), n_turns=2)[0]
    f = tmp_path / f"{spec.conv_id}.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in conv.to_records()) + "\n")

    loaded_spec, messages, _meta = load_conversation(f)
    assert loaded_spec == spec
    prompt = judge_turn_prompts(s, messages)[-1][2]
    assert spec.conv_id not in prompt and "harmful" not in prompt.lower().split("## definitions")[0]
    for c in CONDITIONS:
        assert OBJECTIVES[c].format(product=s.product) not in prompt
    assert "Agent (turn 1)" in prompt and "Agent (turn 2)" in prompt
