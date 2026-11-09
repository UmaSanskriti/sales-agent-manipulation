"""Information-flow checks: each model sees only what it should.

  agent (gpt-oss)  : company materials + condition objective + the customer's words.
                     Never persona text or the customer's private situation and needs.
  simulator (Haiku): persona + customer situation and needs + transcript.
                     Never the agent's system prompt, facts, objective or condition.
  judge            : facts + numbered transcript. Never the condition / objective.
"""
from prompts.prompts import (
    CONDITIONS,
    CUSTOMER_NEEDS,
    CUSTOMER_SITUATION,
    OBJECTIVES,
    PERSONAS,
    render_judge_prompt,
    render_sop,
    render_system_prompt,
)
from src.first_messages import render_first_message_prompt
from src.llm import MockClient
from src.scenarios import load_scenarios
from src.schema import ConvSpec, Message
from src.simulate import clean_customer_message, customer_system_prompt, format_transcript, run_batch

SCENARIOS = load_scenarios()


def agent_only_strings(s):
    objectives = [OBJECTIVES[c].format(product=s.product) for c in CONDITIONS]
    return s.facts + s.limitations + s.pricing + s.terms + [render_sop(s)] + objectives


def persona_only_strings(persona_id, s):
    p = PERSONAS[persona_id]
    return [p["description"], p["behavior"], CUSTOMER_SITUATION, *CUSTOMER_NEEDS.values()]


def test_simulator_and_first_message_prompts_never_contain_agent_side_text():
    for s in SCENARIOS:
        for pid in PERSONAS:
            for prompt in (customer_system_prompt(s, pid), render_first_message_prompt(s, pid)):
                for text in agent_only_strings(s):
                    assert text not in prompt, (s.id, pid, text)


def test_agent_prompt_never_contains_persona_or_customer_situation():
    for s in SCENARIOS:
        for c in CONDITIONS:
            prompt = render_system_prompt(s, c)
            for pid in PERSONAS:
                for text in persona_only_strings(pid, s):
                    assert text not in prompt, (s.id, c, pid)


def test_each_persona_gets_its_own_simulator_prompt():
    s = SCENARIOS[0]
    prompts = {pid: customer_system_prompt(s, pid) for pid in PERSONAS}
    assert len(set(prompts.values())) == len(PERSONAS)
    for pid, prompt in prompts.items():
        assert PERSONAS[pid]["behavior"] in prompt
        for other in PERSONAS:
            if other != pid:
                assert PERSONAS[other]["behavior"] not in prompt
                assert PERSONAS[other]["description"] not in prompt


class Recorder(MockClient):
    def __init__(self, label):
        super().__init__(label)
        self.requests = []

    def chat(self, system, messages, **kw):
        self.requests.append((system, messages))
        return super().chat(system, messages, **kw)


def test_recorded_run_has_clean_information_flow():
    s = SCENARIOS[0]
    items = [(ConvSpec(s.id, pid, c), s, f"hello from {pid}") for pid in PERSONAS for c in CONDITIONS]
    target, sim = Recorder("agent"), Recorder("customer")
    run_batch(items, target, sim, n_turns=3)

    persona_text = [t for pid in PERSONAS for t in persona_only_strings(pid, s)]
    for system, messages in target.requests:
        blob = system + " ".join(m["content"] for m in messages)
        assert not any(t in blob for t in persona_text)
        assert all(m["role"] in ("user", "assistant") for m in messages)
    agent_prompts = {render_system_prompt(s, c) for c in CONDITIONS}
    assert {sys for sys, _ in target.requests} == agent_prompts

    for system, messages in sim.requests:
        blob = system + " ".join(m["content"] for m in messages)
        assert not any(t in blob for t in agent_only_strings(s))
        assert not any(p in blob for p in agent_prompts)

    # The simulator is blind to the condition: same persona -> same system prompt in all 3 conditions.
    assert len({sys for sys, _ in sim.requests}) == len(PERSONAS)


def test_judge_prompt_is_condition_blind_and_numbers_agent_turns():
    s = SCENARIOS[0]
    msgs = [Message("customer", "hi", 1), Message("agent", "hello", 1),
            Message("customer", "ok", 2), Message("agent", "sure", 2)]
    prompt = render_judge_prompt(s, format_transcript(msgs, number_agent_turns=True), 2)
    assert "Agent (turn 1): hello" in prompt and "Agent (turn 2): sure" in prompt
    for c in CONDITIONS:
        assert OBJECTIVES[c].format(product=s.product) not in prompt
    assert "Agent: " not in format_transcript(msgs, number_agent_turns=True)
    assert "Agent: hello" in format_transcript(msgs)  # simulator view stays unnumbered


def test_clean_customer_message():
    assert clean_customer_message('Customer: "Is it worth it?"') == "Is it worth it?"
    assert clean_customer_message("**Customer:** Is it worth it?") == "Is it worth it?"
    assert clean_customer_message("  plain message ") == "plain message"
    assert clean_customer_message("It's a 'deal', right?") == "It's a 'deal', right?"


def test_empty_agent_turns_are_flagged():
    class EmptyAgent(MockClient):
        def chat(self, *a, **k):
            return ""

    s = SCENARIOS[0]
    conv = run_batch([(ConvSpec(s.id, "skeptic", "neutral"), s, "hi")], EmptyAgent(), MockClient("c"), n_turns=2)[0]
    assert conv.metadata["empty_agent_turns"] == 2
