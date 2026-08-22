"""Guards the Alembic setup: exactly one migration head, baseline is a root."""

from alembic.config import Config
from alembic.script import ScriptDirectory


def _script() -> ScriptDirectory:
    return ScriptDirectory.from_config(Config("alembic.ini"))


def test_single_head():
    # More than one head means migrations branched and need merging.
    assert len(_script().get_heads()) == 1


def test_baseline_is_a_root():
    script = _script()
    bases = script.get_bases()
    assert len(bases) == 1
