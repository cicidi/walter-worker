"""scripts/migrate_mem0_to_qdrant_server.py copies points without re-embedding."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

qdrant_client = pytest.importorskip("qdrant_client")
from qdrant_client import QdrantClient, models  # noqa: E402

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "migrate_mem0_to_qdrant_server.py"
_spec = importlib.util.spec_from_file_location("migrate_mem0", _SCRIPT)
migrate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(migrate)


def _mem0_like_store(path: Path, n: int) -> QdrantClient:
    """A collection shaped like mem0's: 4-dim dense + 'bm25' sparse, with payloads."""
    c = QdrantClient(path=str(path))
    c.create_collection(
        "mem0",
        vectors_config=models.VectorParams(size=4, distance=models.Distance.COSINE),
        sparse_vectors_config={"bm25": models.SparseVectorParams(modifier=models.Modifier.IDF)},
    )
    c.upsert("mem0", points=[
        models.PointStruct(
            id=i,
            vector={"": [1.0, float(i), 0.5, 0.25],
                    "bm25": models.SparseVector(indices=[i], values=[1.0])},
            payload={"data": f"lesson {i}", "provenance": "agent"},
        )
        for i in range(n)
    ])
    return c


def test_copies_every_point_with_vectors_and_payload(tmp_path, monkeypatch):
    monkeypatch.setattr(migrate, "BATCH", 7)  # force several scroll pages
    src = _mem0_like_store(tmp_path / "vec", 20)
    dst = QdrantClient(":memory:")

    assert migrate.copy_collection(src, dst, "mem0") == 20

    sparse = dst.get_collection("mem0").config.params.sparse_vectors
    assert sparse["bm25"].modifier == models.Modifier.IDF
    p = dst.retrieve("mem0", ids=[5], with_vectors=True, with_payload=True)[0]
    assert p.payload == {"data": "lesson 5", "provenance": "agent"}
    assert p.vector["bm25"].indices == [5]
    src.close()


def test_rerun_adds_new_local_points_and_keeps_server_only_ones(tmp_path):
    src = _mem0_like_store(tmp_path / "vec", 3)
    dst = QdrantClient(":memory:")
    assert migrate.copy_collection(src, dst, "mem0") == 3

    # Server gets a write of its own; the embedded store gains a point too.
    dst.upsert("mem0", points=[models.PointStruct(
        id=99, vector={"": [0.0, 0.0, 0.0, 1.0]}, payload={"data": "server only"})])
    src.upsert("mem0", points=[models.PointStruct(
        id=3, vector={"": [1.0, 3.0, 0.5, 0.25]}, payload={"data": "lesson 3"})])

    assert migrate.copy_collection(src, dst, "mem0") == 5
    assert dst.retrieve("mem0", ids=[3])[0].payload == {"data": "lesson 3"}
    assert dst.retrieve("mem0", ids=[99])[0].payload == {"data": "server only"}
    src.close()
