"""Tool registry and guarded execution pipeline.

A model-facing capability is a ``Tool`` (name, description, ``run``). The
registry holds them; ``run_tool`` is the single execution path every call flows
through — it times the call, normalizes errors into a ``ToolResult`` (a tool
body never crashes the loop), and emits ``tool_call`` / ``tool_result`` events
for the session log. This mirrors the DeepSeek-Harness tool pipeline: policy,
timing, and logging live around the tool, not inside it.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

# Called with (event_type, payload) for each pipeline event; wiring layers turn
# these into session-log appends. Kept optional so tools stay testable.
EventHook = Callable[[str, Dict[str, Any]], None]


@dataclass
class ToolResult:
    """The normalized outcome of a tool call."""
    name: str
    content: str
    is_error: bool = False
    meta: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Tool(Protocol):
    """A model-facing capability."""
    name: str
    description: str

    def run(self, args: Dict[str, Any]) -> ToolResult:
        ...


class ToolRegistry:
    """A name-keyed set of tools plus their model-facing schemas."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list(self) -> List[Tool]:
        return list(self._tools.values())

    def schemas(self) -> List[Dict[str, str]]:
        """Model-facing tool descriptions (never leaks the run function)."""
        return [{"name": t.name, "description": t.description} for t in self._tools.values()]


def run_tool(
    registry: ToolRegistry,
    name: str,
    args: Dict[str, Any],
    on_event: Optional[EventHook] = None,
) -> ToolResult:
    """Execute one tool call through the pipeline.

    Logs the call before running it, normalizes any failure (unknown tool or a
    raised exception) into an error ``ToolResult``, and logs the result. Never
    raises for a tool-body failure.
    """
    if on_event:
        on_event("tool_call", {"name": name, "args": args})

    started = time.time()
    tool = registry.get(name)
    if tool is None:
        result = ToolResult(name=name, content=f"Unknown tool: {name!r}", is_error=True)
    else:
        try:
            result = tool.run(args)
        except Exception as exc:  # a tool body must not crash the agent loop
            logger.warning("Tool %r failed: %s", name, exc)
            result = ToolResult(name=name, content=f"Tool error: {exc}", is_error=True)

    if on_event:
        on_event(
            "tool_result",
            {
                "name": name,
                "is_error": result.is_error,
                "content": result.content[:2000],
                "duration_s": round(time.time() - started, 3),
                # Structured sources let the UI resolve inline [n] citation
                # markers, and make the session log a provenance record.
                "sources": result.meta.get("sources", []),
            },
        )
    return result


# --------------------------------------------------------------------------
# Concrete tool: search the ingested paper(s).
# --------------------------------------------------------------------------

class PaperSearchTool:
    """Retrieve relevant passages from the ingested paper(s)."""

    name = "paper_search"
    description = (
        "Search the paper(s) for passages relevant to a query. "
        "Input: {\"query\": str}. Returns the most relevant text chunks."
    )

    def __init__(self, paper_ids: List[str], top_k: int = 5, titles: Optional[Dict[str, str]] = None) -> None:
        self.paper_ids = paper_ids
        self.top_k = top_k
        # paper_id -> display title, so citation chips can name the paper.
        self.titles = titles or {}

    def run(self, args: Dict[str, Any]) -> ToolResult:
        query = (args or {}).get("query", "").strip()
        if not query:
            return ToolResult(self.name, "No query provided.", is_error=True)

        from src.core.retriever import PaperRetriever

        retriever = PaperRetriever()
        chunks = retriever.query(query, paper_id=self.paper_ids, top_k=self.top_k)
        if not chunks:
            return ToolResult(self.name, "No relevant passages found.", meta={"count": 0, "sources": []})

        # Evidence is NUMBERED so the model can cite [n] and the UI can resolve
        # each marker to the exact passage it came from.
        parts: List[str] = []
        sources: List[Dict[str, Any]] = []
        for i, chunk in enumerate(chunks, start=1):
            meta = chunk.get("metadata", {})
            paper_id = meta.get("paper_id", "unknown")
            section = meta.get("section") or meta.get("section_type") or ""
            content = chunk.get("content", "")
            title = self.titles.get(paper_id) or meta.get("title") or paper_id

            header = f"[{i}] ({title}{' · ' + section if section else ''})"
            parts.append(f"{header}\n{content}")
            sources.append({
                "index": i,
                "paper_id": paper_id,
                "title": title,
                "section": section,
                "content": content,
                "page_number": meta.get("page_number"),
                "score": chunk.get("score", 0),
            })

        return ToolResult(
            self.name,
            "\n\n---\n\n".join(parts),
            meta={"count": len(chunks), "sources": sources},
        )
