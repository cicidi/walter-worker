"""autoworker/engine.py — the agent spawn, which had no test at all.

The auto-worker's whole value is taking real action, so a spawn that quietly
does not spawn is the worst failure this module can have. Both of the ones
below were found by checking the argv against the installed `claude` CLI
rather than reading the code.
"""
from __future__ import annotations

import pytest

from coworker.autoworker import engine


class TestSpawnAgentInvocation:
    def test_uses_the_headless_print_invocation(self, monkeypatch):
        seen = {}

        class _R:
            returncode = 0
            stdout = '{"result": "ok", "tool_calls": 3}'
            stderr = ""

        def fake_run(argv, **kw):
            seen["argv"] = argv
            seen["kw"] = kw
            return _R()

        monkeypatch.setattr("coworker.autoworker.engine.subprocess.run", fake_run)
        engine._spawn_agent("do the thing", work_dir="/tmp/x", timeout_sec=42)

        argv = seen["argv"]
        assert argv[0] == "claude"
        assert "-p" in argv or "--print" in argv
        # `agent` is not a subcommand and neither of these is a flag: the old
        # argv could never have run.
        assert "agent" not in argv
        assert "--work-dir" not in argv
        assert "--timeout" not in argv
        # Both belong to subprocess, not to claude's argv.
        assert seen["kw"].get("cwd") == "/tmp/x"
        assert seen["kw"].get("timeout") == 42 + 30


class TestToolessFallbackIsNotSuccess:
    """The fallback answered a plain LLM chat and reported success.

    No agent runs, no tool is called, nothing is investigated or fixed — but
    the loop would read `success: True` and count the round as progress. A
    degraded auto-worker is not an auto-worker, and the caller has to be able
    to tell the difference.
    """

    @pytest.fixture
    def no_cli(self, monkeypatch):
        """A machine with no `claude` on PATH.

        LLMClient is stubbed too: the fallback under test calls it, and an
        unstubbed run reaches the real provider — the first version of this
        test did exactly that and got "Hi! Did you mean to type something
        else?" back from a paid API as the agent's output.
        """
        def _raise(argv, **kw):
            raise FileNotFoundError("claude")

        class _LLM:
            def chat(self, *a, **k):
                raise AssertionError("the fallback must not call the LLM at all")

        monkeypatch.setattr("coworker.autoworker.engine.subprocess.run", _raise)
        monkeypatch.setattr("coworker.memory.llm.LLMClient", _LLM)

    def test_missing_cli_does_not_report_success(self, no_cli):
        result = engine._spawn_agent("do the thing")

        assert result["success"] is False
        assert result["tool_calls"] == 0
        assert result["output"], "a failed spawn must say why"

    def test_the_reason_names_the_missing_cli(self, no_cli):
        assert "claude" in engine._spawn_agent("t")["output"].lower()
