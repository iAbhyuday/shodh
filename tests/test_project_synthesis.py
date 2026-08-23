"""Project (multi-paper) synthesis behavior in the agent loop."""

from src.core.agent_loop import (
    RetrieveThenAnswerClient,
    StepEnd,
    ToolCall,
    _build_synthesis_prompt,
    build_project_preamble,
    run_agent_turn,
)
from src.core.tools import ToolRegistry, ToolResult


def test_project_preamble_names_corpus_and_dimensions():
    preamble = build_project_preamble(
        project_name="Robot Learning",
        paper_titles=["Paper A", "Paper B"],
        research_dimensions="Focus on sample efficiency.",
    )
    assert "Robot Learning" in preamble
    assert "- Paper A" in preamble and "- Paper B" in preamble
    assert "Focus on sample efficiency." in preamble
    # Cross-paper synthesis instructions, not single-source answering.
    assert "across papers" in preamble.lower()


def test_project_preamble_without_dimensions_omits_section():
    preamble = build_project_preamble("P", ["Only Paper"])
    assert "RESEARCH DIMENSIONS" not in preamble
    assert "- Only Paper" in preamble


def test_synthesis_prompt_includes_preamble_when_given():
    messages = [
        {"role": "user", "content": "compare the methods"},
        {"role": "tool", "name": "paper_search", "content": "EVIDENCE TEXT"},
    ]
    with_preamble = _build_synthesis_prompt(messages, "PROJECT GUIDANCE HERE")
    assert "PROJECT GUIDANCE HERE" in with_preamble
    assert "EVIDENCE TEXT" in with_preamble

    # Single-paper chat passes no preamble.
    without = _build_synthesis_prompt(messages)
    assert "PROJECT GUIDANCE HERE" not in without


class _FakeDelta:
    def __init__(self, delta):
        self.delta = delta


class _CapturingLLM:
    """Records the prompt it was asked to complete."""

    def __init__(self):
        self.prompt = None

    def stream_complete(self, prompt):
        self.prompt = prompt
        return iter([_FakeDelta("synthesized")])


class _MultiPaperSearchTool:
    name = "paper_search"
    description = "search across papers"

    def __init__(self):
        self.calls = []

    def run(self, args):
        self.calls.append(args)
        return ToolResult(self.name, "[p1] finding one\n\n[p2] finding two")


def test_project_turn_passes_preamble_through_to_the_model():
    tool = _MultiPaperSearchTool()
    registry = ToolRegistry()
    registry.register(tool)

    llm = _CapturingLLM()
    preamble = build_project_preamble("My Project", ["Paper A", "Paper B"])
    client = RetrieveThenAnswerClient(llm, context_preamble=preamble)

    out = "".join(
        run_agent_turn(client, registry, [{"role": "user", "content": "compare them"}])
    )

    assert out == "synthesized"
    assert tool.calls == [{"query": "compare them"}]
    # The synthesis step saw the project guidance and the retrieved evidence.
    assert "My Project" in llm.prompt
    assert "Paper A" in llm.prompt
    assert "finding one" in llm.prompt


def test_single_paper_turn_has_no_project_guidance():
    tool = _MultiPaperSearchTool()
    registry = ToolRegistry()
    registry.register(tool)

    llm = _CapturingLLM()
    client = RetrieveThenAnswerClient(llm)  # no preamble

    "".join(run_agent_turn(client, registry, [{"role": "user", "content": "what is X"}]))
    assert "SYNTHESIS RULES" not in llm.prompt
