"""Tests for the tenancy foundation (User model + default-user bootstrap)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.sql_db import Base, User, DEFAULT_USER_EMAIL, get_or_create_default_user


def _fresh_session():
    engine = create_engine("sqlite://")  # in-memory, isolated from the app DB
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_default_user_created_once():
    db = _fresh_session()
    u1 = get_or_create_default_user(db)
    u2 = get_or_create_default_user(db)
    assert u1.id == u2.id
    assert u1.email == DEFAULT_USER_EMAIL
    assert db.query(User).count() == 1


def test_tenant_columns_exist():
    # user_id is part of the owned tables' schema.
    from src.db.sql_db import UserPaper, Project, Conversation

    assert "user_id" in UserPaper.__table__.columns
    assert "user_id" in Project.__table__.columns
    assert "user_id" in Conversation.__table__.columns
