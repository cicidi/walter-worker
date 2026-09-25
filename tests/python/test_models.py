from __future__ import annotations
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import yaml
from coworker.models import (
    ProjectEntry,
    ProjectCatalog,
    ProjectRef,
    Refs,
    KnowledgePoolEntry,
    GitHubRef,
    SlackRef,
    FeatureConfig,
    FeatureProjectRef,
    LinkRef,
    Decision,
    ReferenceDoc,
)


class TestProjectCatalog:
    def test_empty_catalog(self):
        catalog = ProjectCatalog()
        assert catalog.projects == []

    def test_add_project(self):
        entry = ProjectEntry(name="test", local_path="/tmp/test")
        catalog = ProjectCatalog(projects=[entry])
        assert len(catalog.projects) == 1
        assert catalog.projects[0].name == "test"

    def test_project_with_upstream_downstream(self):
        entry = ProjectEntry(
            name="service-a",
            local_path="/tmp/a",
            upstream=[ProjectRef(name="service-b")],
            downstream=[ProjectRef(name="service-c")],
        )
        assert entry.upstream[0].name == "service-b"
        assert entry.downstream[0].name == "service-c"

    def test_project_with_knowledge_pool(self):
        entry = ProjectEntry(
            name="svc",
            local_path="/tmp/svc",
            knowledge_pool=[
                KnowledgePoolEntry(
                    url="https://wiki.example.com", type="confluence"
                ),
                KnowledgePoolEntry(path="/docs", type="local"),
            ],
        )
        assert len(entry.knowledge_pool) == 2
        assert entry.knowledge_pool[0].type == "confluence"
        assert entry.knowledge_pool[1].type == "local"

    def test_project_with_refs(self):
        entry = ProjectEntry(
            name="svc",
            local_path="/tmp/svc",
            refs=Refs(
                github=[GitHubRef(owner="org", repo="svc")],
                slack=[SlackRef(channel="#svc", id="C123")],
            ),
        )
        assert entry.refs.github[0].owner == "org"
        assert entry.refs.slack[0].channel == "#svc"

    def test_yaml_roundtrip(self):
        catalog = ProjectCatalog(
            projects=[
                ProjectEntry(
                    name="svc",
                    local_path="/tmp/svc",
                    repo="git@github.com:org/svc.git",
                    env={"KEY": "val"},
                    upstream=[ProjectRef(name="dep1")],
                    knowledge_pool=[
                        KnowledgePoolEntry(
                            url="https://wiki", type="confluence"
                        )
                    ],
                )
            ]
        )
        data = catalog.model_dump(exclude_none=True)
        yaml_str = yaml.dump(data, default_flow_style=False)
        loaded = ProjectCatalog(**yaml.safe_load(yaml_str))
        assert loaded.projects[0].name == "svc"
        assert loaded.projects[0].upstream[0].name == "dep1"


class TestFeatureConfig:
    def test_minimal_creation(self):
        config = FeatureConfig(name="test-init")
        assert config.name == "test-init"
        assert config.status == "active"
        assert config.projects == []

    def test_full_config(self):
        config = FeatureConfig(
            name="auth-migration",
            description="Migrate auth to OAuth2",
            status="active",
            created="2026-06-11",
            projects=[
                FeatureProjectRef(
                    name="auth-service",
                    role="upstream",
                    branches=["main", "feat/oauth2"],
                )
            ],
            links=[LinkRef(url="https://wiki", title="Design Doc")],
            decisions=[
                Decision(
                    date="2026-06-01",
                    decision="Use OAuth2",
                    rationale="Standard",
                    by="cicidi",
                )
            ],
            reference_docs=[ReferenceDoc(path="~/docs/spec.md", title="Spec")],
        )
        assert len(config.projects) == 1
        assert config.projects[0].branches == ["main", "feat/oauth2"]
        assert config.decisions[0].by == "cicidi"

    def test_default_role(self):
        ref = FeatureProjectRef(name="svc")
        assert ref.role == "peer"

    def test_yaml_roundtrip(self):
        config = FeatureConfig(
            name="test-init",
            description="Test",
            projects=[
                FeatureProjectRef(name="svc", branches=["main"])
            ],
            links=[LinkRef(url="https://x.com", title="X")],
        )
        data = config.model_dump(exclude_none=True)
        yaml_str = yaml.dump(data, default_flow_style=False)
        loaded = FeatureConfig(**yaml.safe_load(yaml_str))
        assert loaded.name == "test-init"
        assert loaded.projects[0].name == "svc"
