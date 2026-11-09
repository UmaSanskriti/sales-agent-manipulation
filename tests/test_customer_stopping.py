import json

import pytest

from prompts.prompts import OBJECTIONS
from src.llm import MockClient
from src.scenarios import load_scenarios
from src.schema import ConvSpec
from src.simulate import parse_customer_reply, run_batch


class ScriptedCustomer(MockClient):
    def __init__(self):
        super().__init__("customer")
        self.rounds = []

    def chat_many(self, requests, **kw):
        self.rounds.append(len(requests))
        replies = []
        for _, messages in requests:
            transcript = messages[0]["content"]
            if "first stop" in transcript:
                decision = "decline"
            elif "customer follow-up" in transcript:
                decision = "buy"
            else:
                decision = "continue"
            replies.append(json.dumps({"message": "customer follow-up", "decision": decision}))
        return replies


def test_each_conversation_stops_independently_after_matched_opening():
    scenario = load_scenarios()[0]
    items = [(ConvSpec(scenario.id, "anxious", condition), scenario, first)
             for condition, first in [("neutral", "first stop"), ("conversion", "first continue")]]
    customer = ScriptedCustomer()
    conversations = run_batch(items, MockClient("agent"), customer, n_turns=10)
    assert customer.rounds == [2, 1]  # stopped conversation never returns to either model
    assert [c.decision for c in conversations] == ["no", "buy"]
    assert [c.metadata["actual_agent_turns"] for c in conversations] == [2, 3]
    for c in conversations:
        assert c.messages[2].content == OBJECTIONS["anxious"].format(product=scenario.product)
        assert c.messages[-1].role == "customer"
        assert c.metadata["stop_reason"] == "customer_decision"
        assert all('"decision"' not in m.content for m in c.messages)


def test_turn_cap_allows_undecided_and_records_actual_length():
    scenario = load_scenarios()[0]
    conv = run_batch([(ConvSpec(scenario.id, "anxious", "neutral"), scenario, "hi")],
                     MockClient("agent"), MockClient("customer"), n_turns=4)[0]
    assert len(conv.messages) == 8
    assert conv.decision == "undecided"
    assert conv.metadata["actual_agent_turns"] == 4
    assert conv.metadata["stop_reason"] == "turn_limit"


@pytest.mark.parametrize("raw", ["plain text", '{}', '[]',
    '{"message":"hi","decision":"maybe"}',
    '{"message":"","decision":"continue"}'])
def test_malformed_customer_replies_are_not_treated_as_conversation(raw):
    with pytest.raises(ValueError):
        parse_customer_reply(raw)


def test_fenced_json_is_accepted():
    assert parse_customer_reply('```json\n{"message":"I need time.","decision":"leave_undecided"}\n```') == (
        "I need time.", "leave_undecided")


def test_customer_can_leave_undecided_without_hitting_cap():
    class Leaves(MockClient):
        def chat(self, *args, **kwargs):
            return '{"message":"I need time.","decision":"leave_undecided"}'

    scenario = load_scenarios()[0]
    conv = run_batch([(ConvSpec(scenario.id, "anxious", "neutral"), scenario, "hi")],
                     MockClient("agent"), Leaves(), n_turns=10)[0]
    assert conv.decision == "undecided"
    assert conv.metadata["stop_reason"] == "customer_decision"
    assert conv.metadata["actual_agent_turns"] == 2
