"""The event-sourced session log.

A conversation's history is an append-only sequence of typed ``SessionEvent``
rows. This is the single source of truth: the model-visible message history is
*derived* from the log via :func:`derive_messages`, never stored separately.

This mirrors the DeepSeek-Harness "model-visible ⟺ logged" rule, adapted to
shodh's SQLAlchemy models. Phase 4 (the streaming agent loop) will make the log
authoritative for what the model sees; for now events are appended alongside the
existing ``Message`` rows.

Event payloads (JSON) by type:
  - user_message       {"content": str}
  - assistant_message  {"content": str, "citations": list, "mode": str|None}
  - retrieval          {"query": str, "paper_ids": list, "count": int}
  - citation           {"citations": list}
  - tool_call          {"name": str, "args": dict}
  - tool_result        {"name": str, "result": Any, "is_error": bool}
  - error              {"message": str}
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db.sql_db import SessionEvent

logger = logging.getLogger(__name__)


class EventType:
    """Session-event type discriminants."""
    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE = "assistant_message"
    RETRIEVAL = "retrieval"
    CITATION = "citation"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"


# Only message-producing events project into the model-visible history.
MODEL_VISIBLE_TYPES = {EventType.USER_MESSAGE, EventType.ASSISTANT_MESSAGE}

# Map an event type to the chat role it derives to.
_TYPE_TO_ROLE = {
    EventType.USER_MESSAGE: "user",
    EventType.ASSISTANT_MESSAGE: "assistant",
}

_MAX_APPEND_RETRIES = 3


def append_event(
    db: Session,
    conversation_id: int,
    event_type: str,
    data: Dict[str, Any],
) -> SessionEvent:
    """Append one typed event, assigning the next per-conversation ``seq``.

    Retries on a unique-constraint race (two appends picking the same seq); the
    ``(conversation_id, seq)`` constraint guarantees at most one winner per slot.
    """
    payload = json.dumps(data, default=str)
    last_error: Optional[Exception] = None

    for _ in range(_MAX_APPEND_RETRIES):
        current_max = (
            db.query(func.max(SessionEvent.seq))
            .filter(SessionEvent.conversation_id == conversation_id)
            .scalar()
        )
        next_seq = (current_max or 0) + 1
        event = SessionEvent(
            conversation_id=conversation_id,
            seq=next_seq,
            type=event_type,
            data=payload,
        )
        db.add(event)
        try:
            db.commit()
            db.refresh(event)
            return event
        except IntegrityError as exc:  # seq taken by a concurrent append; retry
            db.rollback()
            last_error = exc

    raise RuntimeError(
        f"Failed to append {event_type} event to conversation {conversation_id} "
        f"after {_MAX_APPEND_RETRIES} attempts"
    ) from last_error


# -- typed append helpers ---------------------------------------------------

def append_user_message(db: Session, conversation_id: int, content: str) -> SessionEvent:
    return append_event(db, conversation_id, EventType.USER_MESSAGE, {"content": content})


def append_assistant_message(
    db: Session,
    conversation_id: int,
    content: str,
    citations: Optional[List[dict]] = None,
    mode: Optional[str] = None,
) -> SessionEvent:
    return append_event(
        db,
        conversation_id,
        EventType.ASSISTANT_MESSAGE,
        {"content": content, "citations": citations or [], "mode": mode},
    )


def append_retrieval(
    db: Session,
    conversation_id: int,
    query: str,
    paper_ids: List[str],
    count: int,
) -> SessionEvent:
    return append_event(
        db,
        conversation_id,
        EventType.RETRIEVAL,
        {"query": query, "paper_ids": paper_ids, "count": count},
    )


def append_error(db: Session, conversation_id: int, message: str) -> SessionEvent:
    return append_event(db, conversation_id, EventType.ERROR, {"message": message})


# -- reads / projection -----------------------------------------------------

def get_events(db: Session, conversation_id: int) -> List[SessionEvent]:
    """All events for a conversation, in log order."""
    return (
        db.query(SessionEvent)
        .filter(SessionEvent.conversation_id == conversation_id)
        .order_by(SessionEvent.seq.asc())
        .all()
    )


def derive_messages(events: List[SessionEvent]) -> List[Dict[str, str]]:
    """Project model-visible ``{role, content}`` messages from the log.

    Only message-producing events (user/assistant) contribute; retrieval,
    citation, tool, and error events stay in the log but out of the model's view.
    """
    messages: List[Dict[str, str]] = []
    for event in events:
        role = _TYPE_TO_ROLE.get(event.type)
        if role is None:
            continue
        try:
            content = json.loads(event.data).get("content", "")
        except (json.JSONDecodeError, TypeError):
            content = ""
        messages.append({"role": role, "content": content})
    return messages


def event_to_dict(event: SessionEvent) -> Dict[str, Any]:
    """Serialize an event for API responses."""
    try:
        data = json.loads(event.data)
    except (json.JSONDecodeError, TypeError):
        data = {}
    return {
        "seq": event.seq,
        "type": event.type,
        "data": data,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
