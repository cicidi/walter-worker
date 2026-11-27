#!/usr/bin/env bash
# SessionStart hook: register the session and make sure its folder has an
# initiative.
#
# Every session gets its own record under analytics/sessions/<session_id>.
# The initiative is read from CLAUDE.local.md in the session's project folder
# (the git root, or the folder itself when it is not a repo). A folder under
# $HOME that has no CLAUDE.local.md of its own inherits $HOME/CLAUDE.local.md,
# whose initiative belongs to some other project; the agent then loads the
# wrong context and the status bar shows the wrong name. So when the project
# folder has no initiative marker of its own, tell the agent to ask the user
# to create one before doing anything else.
source "${0%/*}/common.sh"
raw=$(cat)
ensure_session "$raw"

# One interpreter reads the payload and builds the reply (see test_hooks.py).
RAW="$raw" SID="$SESSION_ID" python3 -c '
import json, os, re, subprocess
try:
    cwd = json.loads(os.environ["RAW"]).get("cwd") or os.getcwd()
except ValueError:
    cwd = os.getcwd()
r = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                   capture_output=True, text=True)
project = r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else cwd
local_md = os.path.join(project, "CLAUDE.local.md")
name = None
if os.path.isfile(local_md):
    with open(local_md, encoding="utf-8", errors="replace") as f:
        m = re.search(r"<!--\s*(?:FEATURE|INITIATIVE):(\S+)\s+START\s*-->", f.read())
    name = m.group(1) if m else None
sid = os.environ["SID"]
if name:
    msg = f"Session {sid}. Initiative: {name} (from {local_md})."
else:
    msg = (
        f"Session {sid}. The project folder {project} has no initiative: "
        f"no FEATURE or INITIATIVE marker in {local_md}. Any initiative that "
        "appears in a CLAUDE.local.md of a parent folder belongs to another "
        "project; do not treat it as this session initiative. Before any other "
        "work, ask the user whether to create an initiative for this folder: "
        "list the existing ones with coworker feature list and suggest a name "
        "based on the folder. On a new name run "
        f"coworker feature start <name> -p {project}; on an existing one run "
        f"coworker feature activate <name> -p {project}. Either command "
        f"creates {local_md}. Tell the user to restart the session afterwards "
        "so the new context loads."
    )
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "SessionStart", "additionalContext": msg}}))
'
