#!/usr/bin/env python3
"""Copy mem0's embedded Qdrant store to a Qdrant server.

Embedded Qdrant (~/.coworker/memory/vector) locks its folder to one process,
so the dashboard, the Stop hook and the memory MCP servers fought over it.
After this copy, set COWORKER_QDRANT_URL and every process shares the server.

Points are copied with their stored vectors and payloads, so nothing is
re-embedded. Upserts are keyed by point id, so re-running it adds whatever
the embedded store gained since the last run (for example, memories captured
by processes that had not switched to the server yet). Points that exist only
on the server are kept. Stop every process that uses mem0 first: the embedded
store can only be opened by one process.

Usage:
    python3 scripts/migrate_mem0_to_qdrant_server.py [--src DIR] [--url URL]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from qdrant_client import QdrantClient, models

BATCH = 256


def copy_collection(src: QdrantClient, dst: QdrantClient, name: str) -> int:
    """Copy one collection; return the number of points on the server after."""
    params = src.get_collection(name).config.params
    if not dst.collection_exists(name):
        dst.create_collection(
            name,
            vectors_config=params.vectors,
            sparse_vectors_config=params.sparse_vectors,
        )

    offset = None
    while True:
        points, offset = src.scroll(
            name, limit=BATCH, offset=offset, with_payload=True, with_vectors=True
        )
        if points:
            dst.upsert(
                name,
                points=[
                    models.PointStruct(id=p.id, vector=p.vector, payload=p.payload)
                    for p in points
                ],
                wait=True,
            )
        if offset is None:
            break
    return dst.count(name, exact=True).count


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default="~/.coworker/memory/vector")
    ap.add_argument("--url", default="http://localhost:6333")
    args = ap.parse_args()

    src_path = Path(args.src).expanduser()
    if not src_path.is_dir():
        print(f"no embedded store at {src_path}", file=sys.stderr)
        return 1

    src = QdrantClient(path=str(src_path))
    dst = QdrantClient(url=args.url)
    ok = True
    for c in src.get_collections().collections:
        want = src.count(c.name, exact=True).count
        got = copy_collection(src, dst, c.name)
        status = "ok" if got >= want else "MISMATCH"
        ok &= got >= want
        print(f"  {c.name}: {want} local -> {got} on server  {status}")
    src.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
