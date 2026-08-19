"""Tests for the grounded IdeaGenerationAgent (fakes; no live model)."""

from src.agents.idea_generation_agent import IdeaGenerationAgent
from src.api.schemas import GroundedIdea, IdeaSet


def _agent():
    return IdeaGenerationAgent()


def test_format_evidence_tags_and_sections():
    ev = [
        {"content": "limitation text", "metadata": {"section": "Limitations"}, "score": 0.9},
        {"content": "method text", "metadata": {}, "score": 0.5},
    ]
    out = IdeaGenerationAgent._format_evidence(ev)
    assert "[E1] (Limitations) limitation text" in out
    assert "[E2] method text" in out


def test_format_idea_markdown():
    idea = GroundedIdea(
        hypothesis="Try X on Y",
        rationale="because Z",
        suggested_experiment="run baseline B",
        novelty="unexplored",
    )
    s = IdeaGenerationAgent._format_idea(idea)
    assert s.startswith("**Try X on Y**")
    assert "because Z" in s
    assert "_Experiment:_ run baseline B" in s
    assert "_Novelty:_ unexplored" in s


def test_gather_evidence_dedupes_and_caps(monkeypatch):
    # Fake retriever: every probe returns the same two chunks -> dedup to two.
    class _FakeRetriever:
        def query(self, probe, paper_id=None, top_k=5):
            return [
                {"content": "chunk A", "metadata": {}, "score": 0.8},
                {"content": "chunk B", "metadata": {}, "score": 0.4},
            ]

    import src.core.retriever as retriever_mod
    monkeypatch.setattr(retriever_mod, "PaperRetriever", _FakeRetriever)

    agent = IdeaGenerationAgent(max_evidence=8)
    evidence = agent._gather_evidence("paper-1")
    assert [c["content"] for c in evidence] == ["chunk A", "chunk B"]  # deduped, score-sorted


def test_generate_ideas_end_to_end_returns_strings(monkeypatch):
    class _FakeRetriever:
        def query(self, probe, paper_id=None, top_k=5):
            return [{"content": "the method fails on long inputs", "metadata": {"section": "Limitations"}, "score": 1.0}]

    import src.core.retriever as retriever_mod
    monkeypatch.setattr(retriever_mod, "PaperRetriever", _FakeRetriever)

    agent = IdeaGenerationAgent()
    # Fake structured-output program: returns an IdeaSet regardless of prompt.
    agent._program = lambda **kwargs: IdeaSet(
        ideas=[GroundedIdea(hypothesis="Handle long inputs", rationale="fails on long inputs", grounded_in=["E1"])]
    )

    out = agent.generate_ideas({"paper_id": "p1", "title": "T"})
    assert out == ["**Handle long inputs** fails on long inputs"]


def test_generate_ideas_falls_back_to_abstract_when_not_ingested(monkeypatch):
    class _EmptyRetriever:
        def query(self, probe, paper_id=None, top_k=5):
            return []  # not ingested

    import src.core.retriever as retriever_mod
    monkeypatch.setattr(retriever_mod, "PaperRetriever", _EmptyRetriever)

    captured = {}

    def _fake_program(**kwargs):
        captured.update(kwargs)
        return IdeaSet(ideas=[GroundedIdea(hypothesis="From abstract")])

    agent = IdeaGenerationAgent()
    agent._program = _fake_program

    out = agent.generate_ideas({"paper_id": "p1", "title": "T", "abstract": "ABSTRACT BODY"})
    assert out == ["**From abstract**"]
    assert "ABSTRACT BODY" in captured["evidence"]  # abstract used as evidence


def test_generate_ideas_empty_when_no_evidence_and_no_abstract(monkeypatch):
    class _EmptyRetriever:
        def query(self, probe, paper_id=None, top_k=5):
            return []

    import src.core.retriever as retriever_mod
    monkeypatch.setattr(retriever_mod, "PaperRetriever", _EmptyRetriever)

    agent = IdeaGenerationAgent()
    assert agent.generate_ideas({"paper_id": "p1", "title": "T"}) == []
