"""The CLI must import with only the declared dependencies installed.

`coworker.cli` imports `coworker.memory.cli_memory` to register the `memory`
command group, which used to drag in the whole `coworker.memory` package and,
through it, openai, mem0, networkx and graphify. None of those are dependencies
of this project - graphify has no distribution at all - so a fresh
`pip install` produced a CLI that raised ModuleNotFoundError on every
invocation, including `coworker status`.

Runs in a subprocess so the modules are genuinely absent from a clean
interpreter rather than already present in the test process.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"

# Mirrors what a base `pip install walter-worker` would not provide.
_OPTIONAL_MODULES = ("openai", "mem0", "networkx", "graphify")

_BLOCK_AND_RUN = """
import sys

BLOCK = set({block!r})


class Blocker:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in BLOCK:
            raise ModuleNotFoundError(
                "No module named {{!r}} (simulating a base install)".format(name)
            )
        return None


sys.meta_path.insert(0, Blocker())
sys.path.insert(0, {src!r})

import coworker.cli
from click.testing import CliRunner

runner = CliRunner()
for args in (["--help"], ["status"], ["memory", "--help"]):
    result = runner.invoke(coworker.cli.main, args)
    assert result.exit_code == 0, "{{}} failed: {{}}".format(args, result.output)

print("CLI_IMPORT_OK")
"""


def _run_with_optional_modules_blocked():
    script = _BLOCK_AND_RUN.format(block=_OPTIONAL_MODULES, src=str(SRC))
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        timeout=120,
    )


def test_cli_imports_without_optional_memory_dependencies():
    proc = _run_with_optional_modules_blocked()
    assert proc.returncode == 0, (
        "the CLI failed to import or run without the optional memory "
        f"dependencies:\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert "CLI_IMPORT_OK" in proc.stdout


def test_memory_exports_still_resolve_lazily():
    """The lazy re-exports must behave like real attributes."""
    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "import coworker.memory as m\n"
        "assert 'LLMClient' in m.__all__\n"
        "try:\n"
        "    m.definitely_not_an_export\n"
        "except AttributeError:\n"
        "    print('LAZY_OK')\n"
        "else:\n"
        "    raise SystemExit('unknown attribute did not raise')\n"
    ) % str(SRC)
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert "LAZY_OK" in proc.stdout
