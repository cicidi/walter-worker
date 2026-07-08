"""Top-level test config: import paths + the hermetic install fixture.

Every test that needs an "installed" coworker uses `installed_home`, which runs
setup/install.sh against a throwaway HOME with a local fake skill-factory
(never touches the network). No test may read the developer's real ~/.claude
or ~/.coworker.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
# Make both `import coworker` (src on path) and `from src.coworker...` work.
for _p in (str(_SRC), str(_REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _git_env() -> dict:
    base = {
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@test",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@test",
    }
    return {**os.environ, **base}


@pytest.fixture(scope="session")
def installed_home(tmp_path_factory) -> Path:
    """Run setup/install.sh --global into a throwaway HOME.

    Pre-seeds a local fake skill-factory git repo so install.sh takes its
    'already cloned' branch (git pull fails offline -> warn -> continue) and
    never clones from GitHub. Yields the temp HOME.
    """
    home = tmp_path_factory.mktemp("home")

    # Fake skill-factory so install.sh does NOT git clone from GitHub.
    sf = home / ".config" / "opencode" / "skills" / "skill-factory"
    sf.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=sf, check=True)
    (sf / "README.md").write_text("fake skill-factory for tests\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(sf), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(sf), "commit", "-q", "-m", "init"],
                   check=True, env=_git_env())

    env = {**os.environ, "HOME": str(home)}
    # install.sh reads mode/skill-selection interactively; pipe '1' on stdin.
    proc = subprocess.run(
        ["bash", str(_REPO_ROOT / "setup" / "install.sh"), "--global"],
        input="1\n", text=True, env=env, cwd=str(_REPO_ROOT),
        capture_output=True, timeout=90,
    )
    # install.sh should succeed; surface stderr if it didn't.
    assert proc.returncode == 0, f"install.sh failed:\n{proc.stderr}"
    yield home
