"""The analytics hooks run on every prompt and tool call, but had no tests.

They are shell, they write the session record, and they run unattended — so a
quoting mistake silently corrupts telemetry rather than failing loudly.
"""
import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
HOOKS = REPO / "src" / "coworker" / "analytics" / "hooks"


def _run_hook(hook: str, payload: dict, home: Path, cwd: Path) -> Path:
    """Run a hook with `payload` on stdin, a temp HOME, and a chosen cwd."""
    env = {**os.environ, "HOME": str(home)}
    proc = subprocess.run(
        ["bash", str(HOOKS / hook)],
        input=json.dumps(payload), text=True, env=env, cwd=str(cwd),
        capture_output=True, timeout=60,
    )
    assert proc.returncode == 0, f"{hook} failed: {proc.stderr}"
    return home / ".coworker" / "analytics" / "sessions"


def test_session_yaml_is_valid_when_cwd_contains_a_quote(tmp_path):
    """A cwd with a `"` used to close the YAML scalar early.

    session.yaml is written with double-quoted scalars, so an unescaped quote
    made the whole file unparseable — every real YAML reader lost the session's
    metadata, and the line-based reader in this repo silently truncated the path.
    """
    home = tmp_path / "home"
    home.mkdir()
    quoted = tmp_path / 'dir-with-"quote"'
    quoted.mkdir()

    sessions = _run_hook(
        "on-user-prompt.sh",
        {"session_id": "quote-test", "prompt": "hi"},
        home, quoted,
    )

    written = sessions / "quote-test" / "session.yaml"
    assert written.is_file()
    data = yaml.safe_load(written.read_text())
    assert data["cwd"] == str(quoted), "cwd must round-trip exactly"
    assert data["session_id"] == "quote-test"


def test_plain_cwd_still_writes_valid_yaml(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    plain = tmp_path / "plain"
    plain.mkdir()

    sessions = _run_hook(
        "on-user-prompt.sh",
        {"session_id": "plain-test", "prompt": "hi"},
        home, plain,
    )

    data = yaml.safe_load((sessions / "plain-test" / "session.yaml").read_text())
    assert data["cwd"] == str(plain)


@pytest.mark.parametrize(
    "prompt",
    [
        'he said "hi"',
        "back\\slash and `tick`",
        "multi\nline\twith %s and $VAR",
        "unicode 中文 🎯",
    ],
)
def test_prompt_content_is_json_escaped(tmp_path, prompt):
    """Arbitrary prompt text must not break the messages.jsonl record."""
    home = tmp_path / "home"
    home.mkdir()
    cwd = tmp_path / "plain"
    cwd.mkdir()

    sessions = _run_hook(
        "on-user-prompt.sh",
        {"session_id": "escape-test", "prompt": prompt},
        home, cwd,
    )

    lines = (sessions / "escape-test" / "messages.jsonl").read_text().splitlines()
    assert lines, "the hook wrote nothing"
    for line in lines:
        record = json.loads(line)  # raises if the escaping is wrong
        assert prompt in record["content"]


def test_tool_args_with_quotes_stay_valid_json(tmp_path):
    """tool_input is arbitrary; the record must survive a nested awkward value."""
    home = tmp_path / "home"
    home.mkdir()
    cwd = tmp_path / "plain"
    cwd.mkdir()

    tool_input = {"command": 'echo "hi" && ls \\tmp', "nested": {"a": [1, 2]}}
    sessions = _run_hook(
        "on-pre-tool.sh",
        {
            "session_id": "tool-test",
            "tool_name": "Bash",
            "tool_use_id": "call_abc",
            "tool_input": tool_input,
        },
        home, cwd,
    )

    lines = (sessions / "tool-test" / "tools.jsonl").read_text().splitlines()
    assert lines
    record = json.loads(lines[0])
    assert record["tool"] == "Bash"
    assert record["args"] == tool_input


class TestPayloadShapeMatchesClaudeCode:
    """The hooks parsed a `data` wrapper that Claude Code has never sent.

    Every hook event delivers flat top-level keys — `prompt`, `tool_name`,
    `tool_response` — as siblings of `session_id`, not nested under `data`.
    (Reference: https://code.claude.com/docs/en/hooks, which shows `prompt` as
    a sibling of `session_id` and contains no `data` container at all.)

    The fixtures in this file were written from the same wrong belief as the
    code, so the suite stayed green while production recorded nothing: every
    user prompt in ~/.coworker/analytics was the string "\\n", and 97% of the
    tool results Claude Code produced were empty. OpenCode's own plugin, which
    reads the fields correctly, had 100% of its results populated — the data
    was always there.
    """

    def test_user_prompt_is_recorded(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        cwd = tmp_path / "proj"
        cwd.mkdir()

        sessions = _run_hook(
            "on-user-prompt.sh",
            {"session_id": "flat-1", "hook_event_name": "UserPromptSubmit",
             "cwd": str(cwd), "prompt": "the deploy broke at midnight"},
            home, cwd,
        )

        lines = (sessions / "flat-1" / "messages.jsonl").read_text().splitlines()
        record = json.loads(lines[0])
        assert record["content"] == "the deploy broke at midnight"

    def test_tool_result_is_recorded(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        cwd = tmp_path / "proj"
        cwd.mkdir()

        sessions = _run_hook(
            "on-post-tool.sh",
            {"session_id": "flat-2", "hook_event_name": "PostToolUse",
             "cwd": str(cwd), "tool_name": "Bash", "tool_use_id": "toolu_1",
             "tool_input": {"command": "pytest"}, "tool_response": "3 passed",
             "duration_ms": 12},
            home, cwd,
        )

        lines = (sessions / "flat-2" / "tools.jsonl").read_text().splitlines()
        record = json.loads(lines[0])
        assert record["tool"] == "Bash"
        assert "3 passed" in record["result"]
