"""Tests for the event-sourced session log."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.sql_db import Base, Conversation, SessionEvent
from src.core import session_log
from src.core.session_log import EventType


def _fresh_session():
    engine = create_engine("sqlite://")  # in-memory
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _new_conversation(db) -> int:
    conv = Conversation(title="t")
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv.id


def test_seq_is_monotonic_per_conversation():
    db = _fresh_session()
    c1 = _new_conversation(db)
    c2 = _new_conversation(db)

    e1 = session_log.append_user_message(db, c1, "hi")
    e2 = session_log.append_assistant_message(db, c1, "hello")
    e3 = session_log.append_user_message(db, c2, "other convo")

    assert (e1.seq, e2.seq) == (1, 2)
    assert e3.seq == 1  # independent sequence per conversation


def test_derive_messages_projects_only_model_visible():
    db = _fresh_session()
    c = _new_conversation(db)

    session_log.append_user_message(db, c, "what is X?")
    session_log.append_retrieval(db, c, "X", ["p1"], 3)  # not model-visible
    session_log.append_assistant_message(db, c, "X is Y", citations=[{"p": 1}], mode="agent")
    session_log.append_error(db, c, "some error")  # not model-visible

    messages = session_log.derive_messages(session_log.get_events(db, c))
    assert messages == [
        {"role": "user", "content": "what is X?"},
        {"role": "assistant", "content": "X is Y"},
    ]


def test_events_are_ordered_and_serializable():
    db = _fresh_session()
    c = _new_conversation(db)
    session_log.append_user_message(db, c, "q")
    session_log.append_assistant_message(db, c, "a", citations=[{"x": 1}], mode="contextual")

    events = session_log.get_events(db, c)
    assert [e.seq for e in events] == [1, 2]

    dumped = [session_log.event_to_dict(e) for e in events]
    assert dumped[0]["type"] == EventType.USER_MESSAGE
    assert dumped[0]["data"]["content"] == "q"
    assert dumped[1]["type"] == EventType.ASSISTANT_MESSAGE
    assert dumped[1]["data"]["citations"] == [{"x": 1}]
    assert dumped[1]["data"]["mode"] == "contextual"


def test_unique_constraint_present():
    assert "uq_session_event_conv_seq" in {
        c.name for c in SessionEvent.__table__.constraints if c.name
    }
