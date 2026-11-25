# Qdrant server for coworker memory

## Why

mem0 stores memories in Qdrant. By default it runs Qdrant **embedded** in
whichever process calls it, with its data in `~/.coworker/memory/vector`.
Embedded Qdrant locks that folder to one process. The dashboard, the Stop
hook (`coworker memory capture` / `curate`) and every memory MCP server all
open it, so whoever comes second fails, and the code turns that failure into
an empty result. Memories silently go unsaved, and the dashboard shows 0.

A Qdrant **server** accepts many clients at once. When `COWORKER_QDRANT_URL`
is set, `Mem0Client.from_config()` connects to it instead of the folder.

## Set up (Linux, systemd user service)

1. Install the server binary. Match the minor version of the installed
   `qdrant-client` (`pip show qdrant-client`); client and server may differ by
   at most one minor version.

   ```bash
   gh release download v1.18.3 -R qdrant/qdrant -p 'qdrant-x86_64-unknown-linux-gnu.tar.gz'
   tar -xzf qdrant-x86_64-unknown-linux-gnu.tar.gz
   install -m755 qdrant ~/.local/bin/qdrant
   ```

2. Start it as a user service. It listens on 127.0.0.1:6333 only and keeps its
   data in `~/.coworker/memory/qdrant-server/`.

   ```bash
   mkdir -p ~/.coworker/memory/qdrant-server
   install -Dm644 setup/qdrant/coworker-qdrant.service ~/.config/systemd/user/
   systemctl --user daemon-reload
   systemctl --user enable --now coworker-qdrant
   curl -s localhost:6333/        # {"title":"qdrant - vector search engine",...}
   ```

   For it to start at boot without a login, run `loginctl enable-linger $USER`.

3. Copy the existing memories. Close Claude Code and OpenCode sessions and the
   dashboard first, so nothing holds the folder. Back it up, then copy:

   ```bash
   cp -a ~/.coworker/memory/vector ~/.coworker/backups/memory-vector-$(date -u +%Y%m%dT%H%M%SZ)
   python3 scripts/migrate_mem0_to_qdrant_server.py
   #   mem0: 2488 local -> 2488 on server  ok
   ```

   Vectors are copied as stored; nothing is re-embedded. Re-running is safe
   and adds anything new in the folder.

4. Point every process at the server. Add this where `DEEPSEEK_API_KEY` is set
   (for example `~/.zshrc`), then restart Claude Code and OpenCode sessions so
   hooks and MCP servers pick it up:

   ```bash
   export COWORKER_QDRANT_URL=http://localhost:6333
   ```

## Undo

Remove the `COWORKER_QDRANT_URL` line and restart sessions. mem0 goes back to
`~/.coworker/memory/vector`. Memories saved only on the server stay there.
Stop the service with `systemctl --user disable --now coworker-qdrant`.
