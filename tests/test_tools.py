"""Tests for the tool registry and guarded execution pipeline."""

import pytest

from src.core.tools import Tool, ToolRegistry, ToolResult, run_tool


class _EchoTool:
    name = "echo"
    description = "echoes its query"

    def run(self, args):
        return ToolResult(self.name, f"echo: {args.get('query', '')}")


class _BoomTool:
    name = "boom"
    description = "always raises"

    def run(self, args):
        raise RuntimeError("kaboom")


def _registry(*tools):
    reg = ToolRegistry()
    for t in tools:
        reg.register(t)
    return reg


def test_register_and_schemas():
    reg = _registry(_EchoTool())
    assert reg.get("echo") is not None
    assert reg.schemas() == [{"name": "echo", "description": "echoes its query"}]


def test_duplicate_registration_rejected():
    reg = _registry(_EchoTool())
    with pytest.raises(ValueError):
        reg.register(_EchoTool())


def test_run_tool_success_emits_events():
    reg = _registry(_EchoTool())
    events = []
    result = run_tool(reg, "echo", {"query": "hi"}, on_event=lambda t, p: events.append((t, p)))
    assert result.content == "echo: hi"
    assert not result.is_error
    assert [t for t, _ in events] == ["tool_call", "tool_result"]
    assert events[1][1]["is_error"] is False


def test_run_tool_unknown_is_error_not_raise():
    reg = _registry(_EchoTool())
    result = run_tool(reg, "missing", {})
    assert result.is_error
    assert "Unknown tool" in result.content


def test_run_tool_body_exception_is_normalized():
    reg = _registry(_BoomTool())
    result = run_tool(reg, "boom", {})
    assert result.is_error
    assert "kaboom" in result.content


def test_echotool_conforms_to_tool_protocol():
    assert isinstance(_EchoTool(), Tool)
