"""Grounded research-idea generation.

Instead of prompting an LLM with only the title + abstract, this agent grounds
ideas in the ingested full text: it retrieves the passages where research ideas
actually come from (limitations, future work, method, weak results), asks the
model for STRUCTURED ideas that cite that evidence, and optionally checks each
hypothesis against arXiv for novelty.

Public API:
  - generate_ideas(paper) -> List[str]              (backward-compatible; frontend contract)
  - generate_ideas_structured(paper) -> List[GroundedIdea]  (rich objects)

`paper` should carry `paper_id` and `title`; `abstract` and `metrics` are used
when present. When the paper is not ingested, it falls back to the abstract.
"""

from typing import Any, Dict, List
import logging

from src.api.schemas import GroundedIdea, IdeaSet

logger = logging.getLogger(__name__)

# Targeted probes that surface the idea-rich regions of a paper. Retrieval over
# these pulls the limitations / future-work / weak-result passages an abstract
# never contains.
_PROBES = [
    "limitations, weaknesses, failure cases, and threats to validity",
    "future work, open problems, and directions for further research",
    "core method, approach, and key technical contributions",
    "experimental results, benchmarks, ablations, and where the method underperforms",
]

_PROMPT_TEMPLATE = """You are a senior researcher proposing follow-up work.

Paper title: {title}

EVIDENCE (numbered excerpts retrieved from the paper; cite these ids in grounded_in):
{evidence}

Extra structured info about the paper (may be empty):
{metrics}

TASK
Propose {n} NOVEL, specific, testable research ideas that build on THIS paper.
Prioritise ideas that address a stated limitation, improve a weak result, or
transfer the method to a new domain the evidence suggests could work.

RULES
- Ground every idea in the evidence: put the evidence ids you used in grounded_in.
- Do NOT invent findings not supported by the evidence.
- Each hypothesis must be specific and testable (not "explore X further").
- suggested_experiment must be a concrete first step (datasets/baselines/metric).
- Leave novelty as "unknown"; a separate step assesses prior art.
"""


class IdeaGenerationAgent:
    def __init__(self, top_k_per_probe: int = 3, max_evidence: int = 8):
        self.top_k_per_probe = top_k_per_probe
        self.max_evidence = max_evidence
        self._program = None  # lazily built through the provider seam

    def _get_program(self):
        if self._program is None:
            from llama_index.core.program import LLMTextCompletionProgram
            from src.core.llm_factory import LLMFactory

            self._program = LLMTextCompletionProgram.from_defaults(
                output_cls=IdeaSet,
                prompt_template_str=_PROMPT_TEMPLATE,
                llm=LLMFactory.get_llama_index_llm(),
                verbose=False,
            )
        return self._program

    # -- grounding ----------------------------------------------------------
    def _gather_evidence(self, paper_id: str) -> List[Dict[str, Any]]:
        """Retrieve and de-duplicate idea-rich chunks across all probes."""
        from src.core.retriever import PaperRetriever

        retriever = PaperRetriever()
        seen: set = set()
        evidence: List[Dict[str, Any]] = []

        for probe in _PROBES:
            try:
                chunks = retriever.query(probe, paper_id=paper_id, top_k=self.top_k_per_probe)
            except Exception as exc:
                logger.warning("Idea grounding probe failed (paper=%s): %s", paper_id, exc)
                continue
            for chunk in chunks:
                key = (chunk.get("content") or "").strip()[:200]
                if not key or key in seen:
                    continue
                seen.add(key)
                evidence.append(chunk)

        evidence.sort(key=lambda c: c.get("score") or 0.0, reverse=True)
        return evidence[: self.max_evidence]

    @staticmethod
    def _format_evidence(evidence: List[Dict[str, Any]]) -> str:
        lines = []
        for i, chunk in enumerate(evidence, start=1):
            meta = chunk.get("metadata") or {}
            section = meta.get("section") or meta.get("section_type") or ""
            tag = f"[E{i}]" + (f" ({section})" if section else "")
            lines.append(f"{tag} {(chunk.get('content') or '').strip()}")
        return "\n\n".join(lines)

    @staticmethod
    def _format_idea(idea: GroundedIdea) -> str:
        """Render a GroundedIdea to a Markdown string (frontend contract)."""
        parts = [f"**{idea.hypothesis.strip()}**"]
        if idea.rationale:
            parts.append(idea.rationale.strip())
        if idea.suggested_experiment:
            parts.append(f"_Experiment:_ {idea.suggested_experiment.strip()}")
        if idea.novelty and idea.novelty != "unknown":
            note = f" — {idea.novelty_note.strip()}" if idea.novelty_note else ""
            parts.append(f"_Novelty:_ {idea.novelty}{note}")
        return " ".join(parts)

    # -- public API ---------------------------------------------------------
    def generate_ideas_structured(
        self, paper: Dict[str, Any], n: int = 3, check_novelty: bool = False
    ) -> List[GroundedIdea]:
        paper_id = paper.get("paper_id") or paper.get("id")
        title = paper.get("title", "")

        evidence = self._gather_evidence(paper_id) if paper_id else []
        if not evidence and paper.get("abstract"):
            # Not ingested: fall back to the abstract as a single evidence block.
            evidence = [{"content": paper["abstract"], "metadata": {"section": "abstract"}, "score": 1.0}]

        if not evidence:
            logger.info("No evidence for idea generation (paper=%s)", paper_id)
            return []

        try:
            result: IdeaSet = self._get_program()(
                title=title,
                evidence=self._format_evidence(evidence),
                metrics=str(paper.get("metrics") or "{}"),
                n=n,
            )
            ideas = list(result.ideas)
        except Exception as exc:
            logger.exception("Structured idea generation failed (paper=%s): %s", paper_id, exc)
            return []

        if check_novelty:
            ideas = [self._assess_novelty(idea) for idea in ideas]
        return ideas

    def generate_ideas(
        self, paper: Dict[str, Any], n: int = 3, check_novelty: bool = False
    ) -> List[str]:
        """Backward-compatible list-of-strings API used by the frontend."""
        ideas = self.generate_ideas_structured(paper, n=n, check_novelty=check_novelty)
        return [self._format_idea(idea) for idea in ideas]

    # -- optional prior-art check ------------------------------------------
    def _assess_novelty(self, idea: GroundedIdea) -> GroundedIdea:
        """Cheap arXiv prior-art probe (only when check_novelty=True)."""
        try:
            import arxiv

            search = arxiv.Search(
                query=idea.hypothesis, max_results=3, sort_by=arxiv.SortCriterion.Relevance
            )
            hits = list(arxiv.Client().results(search))
            if hits:
                top = hits[0]
                idea.novelty = "similar-to-existing"
                idea.novelty_note = f"Related: '{top.title}' ({top.entry_id})"
            else:
                idea.novelty = "unexplored"
        except Exception as exc:
            logger.warning("Novelty check failed: %s", exc)
            idea.novelty = "unknown"
        return idea
