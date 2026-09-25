from coworker.memory.validate import run_validation, _estimate_tool_calls, _count_incorrect_assumptions, _extract_skill_calls

class TestValidateHelpers:
    def test_estimate_tool_calls(self):
        assert _estimate_tool_calls('no tools') == 0
        assert _estimate_tool_calls('{"tool": "Bash"}') >= 1
    
    def test_count_incorrect(self):
        assert _count_incorrect_assumptions('everything works') == 0
        assert _count_incorrect_assumptions('this is wrong and an error occurred') >= 1
    
    def test_extract_skills(self):
        assert _extract_skill_calls('Skill: test-skill') == ['test-skill']
        assert isinstance(_extract_skill_calls('no skills'), list)

class TestRunValidation:
    def test_basic_run(self, monkeypatch):
        # Patched, because unpatched this spawns two real `claude -p` agents:
        # a unit test that spends money and takes 40 seconds. It used to pass
        # for a worse reason — the invocation failed instantly, and the report
        # has the same keys whether the agents ran or not.
        import coworker.memory.validate as v

        monkeypatch.setattr(
            v, "_run_agent",
            lambda *a, **k: {"success": True, "output": '{"tool": "Bash"}',
                             "tool_calls": 4},
        )
        monkeypatch.setattr(v.time, "sleep", lambda *_: None)

        report = run_validation('print hello')

        assert 'baseline' in report
        assert 'with_memory' in report
        assert report['verdict'] == 'no_change'  # equal counts, both succeeded


class TestAgentInvocation:
    """_run_agent shelled out to `claude agent --prompt … --work-dir … --timeout …`.

    Checked against the installed CLI: there is no `agent` subcommand (claude
    --help lists agents, attach, auth, auto-mode, doctor, gateway, import,
    install, logs, mcp, plugin, project, respawn, rm), `--work-dir` and
    `--timeout` are not flags at all, and `--output-format json` is documented
    as working "only with --print". The command could never succeed.

    test_basic_run passed anyway because it asserts only that the report has
    the right keys — which a run where both agents failed also produces. The
    harness reported a verdict comparing two things that never ran.
    """

    def test_uses_the_headless_print_invocation(self, monkeypatch):
        from coworker.memory.validate import _run_agent

        seen = {}

        class _R:
            returncode = 0
            stdout = '{"result": "ok"}'
            stderr = ""

        def fake_run(argv, **kw):
            seen["argv"] = argv
            seen["kw"] = kw
            return _R()

        monkeypatch.setattr("coworker.memory.validate.subprocess.run", fake_run)
        _run_agent("do the thing", work_dir="/tmp/x", timeout_sec=42)

        argv = seen["argv"]
        assert argv[0] == "claude"
        assert "-p" in argv or "--print" in argv
        assert "agent" not in argv
        assert "--work-dir" not in argv
        assert "--timeout" not in argv
        # The working directory and the timeout belong to subprocess, not to
        # claude's own argv — neither is a flag it accepts.
        assert seen["kw"].get("cwd") == "/tmp/x"
        assert seen["kw"].get("timeout") == 42 + 30

    def test_a_failed_agent_run_is_not_reported_as_a_verdict(self, monkeypatch):
        """Two failed runs must not produce a comparison."""
        from coworker.memory import validate

        monkeypatch.setattr(
            "coworker.memory.validate._run_agent",
            lambda *a, **k: {"success": False, "output": "claude: not found",
                             "tool_calls": 0},
        )

        report = validate.run_validation("some task")

        assert report.get("verdict") in (None, "", "inconclusive")
