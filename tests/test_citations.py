"""The numbered-citation contract: tool numbering -> prompt rules -> sources."""

from src.core.agent_loop import RetrieveThenAnswerClient, _build_synthesis_prompt, run_agent_turn
from src.core.tools import PaperSearchTool, ToolRegistry, run_tool


class _FakeRetriever:
    """Returns two chunks from two different papers."""

    def query(self, query, paper_id=None, top_k=5):
        return [
            {
                "content": "Attention is computed over all tokens.",
                "score": 0.9,
                "metadata": {"paper_id": "p1", "section": "Method"},
            },
            {
                "content": "The method degrades on long inputs.",
                "score": 0.7,
                "metadata": {"paper_id": "p2", "section": "Limitations"},
            },
        ]


def _patch_retriever(monkeypatch):
    import src.core.retriever as retriever_mod
    monkeypatch.setattr(retriever_mod, "PaperRetriever", _FakeRetriever)


def test_tool_numbers_evidence_and_returns_sources(monkeypatch):
    _patch_retriever(monkeypatch)
    tool = PaperSearchTool(["p1", "p2"], titles={"p1": "Paper One", "p2": "Paper Two"})
    result = tool.run({"query": "attention"})

    # Numbered headers the model cites against.
    assert "[1] (Paper One · Method)" in result.content
    assert "[2] (Paper Two · Limitations)" in result.content

    sources = result.meta["sources"]
    assert [s["index"] for s in sources] == [1, 2]
    assert sources[0]["title"] == "Paper One" and sources[0]["paper_id"] == "p1"
    assert sources[1]["title"] == "Paper Two"
    assert sources[1]["content"] == "The method degrades on long inputs."


def test_tool_falls_back_to_paper_id_when_no_title(monkeypatch):
    _patch_retriever(monkeypatch)
    result = PaperSearchTool(["p1", "p2"]).run({"query": "x"})
    assert result.meta["sources"][0]["title"] == "p1"


def test_pipeline_event_carries_sources(monkeypatch):
    _patch_retriever(monkeypatch)
    registry = ToolRegistry()
    registry.register(PaperSearchTool(["p1"], titles={"p1": "Paper One"}))

    events = []
    run_tool(registry, "paper_search", {"query": "q"}, on_event=lambda t, p: events.append((t, p)))

    result_payload = dict(events)["tool_result"]
    assert [s["index"] for s in result_payload["sources"]] == [1, 2]


def test_empty_result_still_reports_sources_key(monkeypatch):
    class _Empty:
        def query(self, *a, **k):
            return []

    import src.core.retriever as retriever_mod
    monkeypatch.setattr(retriever_mod, "PaperRetriever", _Empty)
    result = PaperSearchTool(["p1"]).run({"query": "q"})
    assert result.meta["sources"] == []


def test_prompt_requires_inline_markers():
    prompt = _build_synthesis_prompt(
        [
            {"role": "user", "content": "how does it work"},
            {"role": "tool", "content": "[1] (Paper One)\nsome evidence"},
        ]
    )
    assert "CITATION RULES (REQUIRED)" in prompt
    assert "MUST end with the marker" in prompt
    assert "Never invent a number" in prompt


class _FakeDelta:
    def __init__(self, delta):
        self.delta = delta


class _CitingLLM:
    def stream_complete(self, prompt):
        self.prompt = prompt
        return iter([_FakeDelta("Attention spans all tokens. [1]")])


def test_full_turn_surfaces_numbered_sources(monkeypatch):
    _patch_retriever(monkeypatch)
    registry = ToolRegistry()
    registry.register(PaperSearchTool(["p1", "p2"], titles={"p1": "Paper One", "p2": "Paper Two"}))

    events = []
    out = "".join(
        run_agent_turn(
            RetrieveThenAnswerClient(_CitingLLM()),
            registry,
            [{"role": "user", "content": "how does attention work"}],
            on_event=lambda t, p: events.append((t, p)),
        )
    )

    assert "[1]" in out  # the answer carries an inline marker
    sources = dict(events)["tool_result"]["sources"]
    # ...and the marker resolves to a real source the UI can render.
    assert sources[0]["index"] == 1 and sources[0]["title"] == "Paper One"
