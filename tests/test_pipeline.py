from collections import Counter

from prompts.prompts import CONDITIONS, OBJECTIONS, OBJECTIVES, PERSONAS, render_system_prompt
from src.build_specs import all_specs, pilot_specs
from src.llm import MockClient
from src.scenarios import load_scenarios
from src.schema import ConvSpec
from src.simulate import run_conversation
from src.splits import split_scenarios
from tests.fakes import fake_scenarios


def test_prompts_differ_only_in_objective():
    s = load_scenarios()[0]
    prompts = {c: render_system_prompt(s, c) for c in CONDITIONS}
    objectives = {c: OBJECTIVES[c].format(product=s.product) for c in CONDITIONS}
    stripped = {c: prompts[c].replace(objectives[c], "") for c in CONDITIONS}
    assert len(set(stripped.values())) == 1
    assert len(set(prompts.values())) == 3


def test_conversation_has_10_exchanges_and_fixed_first_two_messages():
    s = load_scenarios()[0]
    convs = [
        run_conversation(ConvSpec(s.id, "skeptic", c), s, "Hi, is this worth it?",
                         MockClient("a"), MockClient("c"), n_turns=10)
        for c in CONDITIONS
    ]
    for conv in convs:
        assert len(conv.messages) == 20
        assert [m.role for m in conv.messages[:2]] == ["customer", "agent"]
        assert conv.messages[0].content == "Hi, is this worth it?"
        assert conv.messages[2].content == OBJECTIONS["skeptic"].format(product=s.product)
        assert conv.decision in ("buy", "no", "undecided")


def test_run_batch_matches_single_and_keeps_order():
    from src.simulate import run_batch

    scenarios = fake_scenarios(1)[:3]
    items = [(ConvSpec(s.id, "analytical", c), s, f"first {i}")
             for i, (s, c) in enumerate(zip(scenarios, CONDITIONS))]
    convs = run_batch(items, MockClient("a"), MockClient("c"), n_turns=4)
    assert [c.spec.scenario_id for c in convs] == [s.id for s in scenarios]
    assert all(len(c.messages) == 8 and c.messages[0].content == f"first {i}" for i, c in enumerate(convs))


def test_threaded_chat_many_preserves_order():
    from src.llm import BaseClient

    class Echo(BaseClient):
        workers = 4

        def chat(self, system, messages, **kw):
            return messages[0]["content"]

    reqs = [("s", [{"role": "user", "content": str(i)}]) for i in range(20)]
    assert Echo().chat_many(reqs) == [str(i) for i in range(20)]


def test_claude_code_command():
    from src.llm import ClaudeCodeClient

    c = ClaudeCodeClient("haiku")
    cmd = c.build_cmd("SYS")
    assert cmd[:2] == ["claude", "-p"] and "--no-session-persistence" in cmd
    assert any(a.startswith("SYS") for a in cmd)
    assert c.render_prompt([{"role": "user", "content": "hi"}]) == "hi"


def test_full_cross_product_size_scales():
    scenarios = load_scenarios()
    assert len(all_specs(scenarios)) == len(scenarios) * len(PERSONAS) * len(CONDITIONS)


def test_pilot_is_stratified():
    scenarios = fake_scenarios(2)
    specs = pilot_specs(scenarios, 10)
    by_id = {s.id: s for s in scenarios}
    assert len(specs) == 30
    assert set(Counter(by_id[x.scenario_id].domain for x in specs).values()) == {6}
    assert {x.persona_id for x in specs} == {"anxious"}
    assert {x.condition for x in specs} == set(CONDITIONS)
    for scenario in scenarios:
        assert {x.condition for x in specs if x.scenario_id == scenario.id} == set(CONDITIONS)


def test_split_is_stratified_by_domain():
    scenarios = fake_scenarios()
    splits = split_scenarios(scenarios)
    by_id = {s.id: s for s in scenarios}
    assert set(splits) == set(by_id)
    for domain in {s.domain for s in scenarios}:
        assert {splits[s.id] for s in scenarios if s.domain == domain} >= {"train"}
