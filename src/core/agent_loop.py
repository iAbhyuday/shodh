"""Turn/step agent loop engine.

A *step* is one model call plus the tools it triggers; a *turn* is a sequence
of steps ending in a final answer (or a step budget). ``run_agent_turn`` drives
the loop: it streams the model's text out to the caller, dispatches any tool
call through the guarded pipeline (:mod:`src.core.tools`), feeds the result back
into the working messages, and emits events for the session log.

The model is behind the ``StepClient`` interface, so the loop's control logic is
fully testable with a scripted fake — no live model needed. A concrete
``RetrieveThenAnswerClient`` provides a deterministic policy (search once, then
synthesize a streamed answer) that is robust on local models; a
model-decides-when-to-call policy can replace it behind the same interface later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Protocol, Union

from src.core.tools import EventHook, ToolRegistry, run_tool


@dataclass
class TextChunk:
    """A streamed piece of the model's visible answer."""
    text: str


@dataclass
class ToolCall:
    """The model's request to call a tool."""
    name: str
    args: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StepEnd:
    """Marks the end of a step. ``finish`` is 'final' or 'tool'."""
    finish: str = "final"


StepChunk = Union[TextChunk, ToolCall, StepEnd]


class StepClient(Protocol):
    """Streams one step given the working messages and the available tools."""

    def stream_step(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, str]]
    ) -> Iterator[StepChunk]:
        ...


def last_user_message(messages: List[Dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content", "")
    return ""


def run_agent_turn(
    client: StepClient,
    registry: ToolRegistry,
    messages: List[Dict[str, Any]],
    on_event: Optional[EventHook] = None,
    max_steps: int = 4,
) -> Iterator[str]:
    """Run one turn, yielding the model's answer text as it streams.

    Tool calls are dispatched through the pipeline (emitting ``tool_call`` /
    ``tool_result`` events via ``on_event``) and their results appended to the
    working messages before the next step. The turn ends when a step produces no
    tool call, or when ``max_steps`` is reached.
    """
    working: List[Dict[str, Any]] = list(messages)

    for _ in range(max_steps):
        pending: Optional[ToolCall] = None

        for chunk in client.stream_step(working, registry.schemas()):
            if isinstance(chunk, TextChunk):
                if chunk.text:
                    yield chunk.text
            elif isinstance(chunk, ToolCall):
                pending = chunk
            elif isinstance(chunk, StepEnd):
                break

        if pending is None:
            return  # a step with no tool call is the final answer

        result = run_tool(registry, pending.name, pending.args, on_event=on_event)
        working.append({"role": "assistant", "content": f"(calling {pending.name} with {pending.args})"})
        working.append({"role": "tool", "name": pending.name, "content": result.content})

    # Step budget exhausted without a tool-free final step; the streamed text so
    # far is the caller's answer.
    return


# --------------------------------------------------------------------------
# Deterministic policy: search once, then synthesize a streamed answer.
# --------------------------------------------------------------------------

def _build_synthesis_prompt(
    messages: List[Dict[str, Any]], context_preamble: Optional[str] = None
) -> str:
    context = "\n\n".join(
        m.get("content", "") for m in messages if m.get("role") == "tool"
    )
    history = "\n".join(
        f"{m['role'].upper()}: {m.get('content', '')}"
        for m in messages
        if m.get("role") in ("user", "assistant") and m.get("content")
    )
    preamble = (
        f"{context_preamble.strip()}\n\n" if context_preamble else ""
    )
    return (
        "You are Shodh AI, a precise research assistant. Answer the user's "
        "question using ONLY the retrieved context below. Use clear Markdown. "
        "If the context is insufficient, say so.\n\n"
        "CITATION RULES (REQUIRED):\n"
        "- The context is numbered [1], [2], ... Every factual sentence you write "
        "MUST end with the marker(s) of the passage(s) it came from, e.g. "
        "'Attention is computed over all tokens. [1]'\n"
        "- Use multiple markers when several passages support one claim: '... [1][3]'\n"
        "- Cite ONLY the numbers that appear in the context. Never invent a number.\n"
        "- Do not add a bibliography or a Sources section; the markers are the citation.\n\n"
        f"{preamble}"
        f"RETRIEVED CONTEXT:\n{context}\n\n"
        f"{history}\nASSISTANT:"
    )


def build_project_preamble(
    project_name: str,
    paper_titles: List[str],
    research_dimensions: Optional[str] = None,
) -> str:
    """Synthesis guidance for a multi-paper (project) conversation.

    Project chat is a different task from single-paper chat: the value is in
    relating findings ACROSS papers, so the preamble names the corpus and asks
    for comparison/contrast rather than a single-source answer.
    """
    papers = "\n".join(f"- {t}" for t in paper_titles) or "- (none listed)"
    dimensions = (
        f"\nRESEARCH DIMENSIONS & GOALS FOR THIS PROJECT:\n{research_dimensions.strip()}\n"
        if research_dimensions
        else ""
    )
    return (
        f'You are synthesizing across the research project "{project_name}".\n'
        f"PAPERS IN THIS PROJECT:\n{papers}\n"
        f"{dimensions}\n"
        "SYNTHESIS RULES:\n"
        "- Relate findings across papers; note agreements, contradictions, and gaps.\n"
        "- Attribute every claim to the paper it came from.\n"
        "- Prefer cross-cutting insight over summarizing one paper in isolation."
    )


class RetrieveThenAnswerClient:
    """A ``StepClient`` that searches once, then streams a grounded answer.

    Step 1 (no tool result yet): request ``paper_search`` for the user's question.
    Step 2 (tool result present): stream the LLM's answer over the retrieved
    context. ``llm`` is any LlamaIndex LLM exposing ``stream_complete``.

    ``context_preamble`` injects task-specific guidance into the synthesis step —
    e.g. :func:`build_project_preamble` for multi-paper project synthesis.
    """

    def __init__(
        self,
        llm: Any,
        tool_name: str = "paper_search",
        context_preamble: Optional[str] = None,
    ) -> None:
        self.llm = llm
        self.tool_name = tool_name
        self.context_preamble = context_preamble

    def stream_step(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, str]]
    ) -> Iterator[StepChunk]:
        has_tool_result = any(m.get("role") == "tool" for m in messages)

        if not has_tool_result:
            yield ToolCall(self.tool_name, {"query": last_user_message(messages)})
            yield StepEnd("tool")
            return

        prompt = _build_synthesis_prompt(messages, self.context_preamble)
        for response in self.llm.stream_complete(prompt):
            yield TextChunk(getattr(response, "delta", "") or "")
        yield StepEnd("final")
