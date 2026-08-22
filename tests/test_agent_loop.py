"""Tests for the turn/step agent loop engine, using scripted fakes."""

from src.core.agent_loop import (
    RetrieveThenAnswerClient,
    StepEnd,
    TextChunk,
    ToolCall,
    run_agent_turn,
)
from src.core.tools import ToolRegistry, ToolResult


class _ScriptedClient:
    """Yields a pre-scripted list of step chunk lists, one list per step."""

    def __init__(self, steps):
        self._steps = list(steps)
        self.seen_tools = []

    def stream_step(self, messages, tools):
        self.seen_tools.append(tools)
        return iter(self._steps.pop(0))


class _SearchTool:
    name = "paper_search"
    description = "search"

    def __init__(self):
        self.calls = []

    def run(self, args):
        self.calls.append(args)
        return ToolResult(self.name, "CONTEXT ABOUT X")


def _registry(tool):
    reg = ToolRegistry()
    reg.register(tool)
    return reg


def test_final_answer_only_streams_text_no_tools():
    client = _ScriptedClient([[TextChunk("hello "), TextChunk("world"), StepEnd("final")]])
    tool = _SearchTool()
    out = "".join(run_agent_turn(client, _registry(tool), [{"role": "user", "content": "hi"}]))
    assert out == "hello world"
    assert tool.calls == []  # no tool dispatched


def test_tool_then_final_dispatches_and_streams():
    client = _ScriptedClient([
        [ToolCall("paper_search", {"query": "X"}), StepEnd("tool")],
        [TextChunk("X is Y"), StepEnd("final")],
    ])
    tool = _SearchTool()
    events = []
    out = "".join(
        run_agent_turn(
            client, _registry(tool), [{"role": "user", "content": "what is X?"}],
            on_event=lambda t, p: events.append(t),
        )
    )
    assert out == "X is Y"
    assert tool.calls == [{"query": "X"}]
    assert events == ["tool_call", "tool_result"]


def test_max_steps_is_respected():
    # Every step asks for a tool and never finalizes.
    tool = _SearchTool()
    client = _ScriptedClient([[ToolCall("paper_search", {"query": "q"}), StepEnd("tool")]] * 10)
    out = "".join(
        run_agent_turn(client, _registry(tool), [{"role": "user", "content": "q"}], max_steps=3)
    )
    assert out == ""
    assert len(tool.calls) == 3  # stopped at the step budget


class _FakeDelta:
    def __init__(self, delta):
        self.delta = delta


class _FakeLLM:
    def stream_complete(self, prompt):
        self.prompt = prompt
        return iter([_FakeDelta("Answer "), _FakeDelta("here")])


def test_retrieve_then_answer_client_drives_a_full_turn():
    tool = _SearchTool()
    client = RetrieveThenAnswerClient(_FakeLLM())
    out = "".join(
        run_agent_turn(client, _registry(tool), [{"role": "user", "content": "what is X?"}])
    )
    assert out == "Answer here"
    assert tool.calls == [{"query": "what is X?"}]  # searched with the user's question
