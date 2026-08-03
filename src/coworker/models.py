from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class McpServer(BaseModel):
    name: str
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True


class Skill(BaseModel):
    name: str
    path: str
    description: str = ""
    enabled: bool = True


class Permissions(BaseModel):
    allow: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)


class ClaudeOverrides(BaseModel):
    effortLevel: str = "medium"
    skipDangerousModePermissionPrompt: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)


class GeminiOverrides(BaseModel):
    extra: dict[str, Any] = Field(default_factory=dict)


class OpenCodeOverrides(BaseModel):
    extra: dict[str, Any] = Field(default_factory=dict)


class CoworkerConfig(BaseModel):
    version: str = "1"
    scope: str = "global"  # global | project

    mcp: list[McpServer] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    permissions: Permissions = Field(default_factory=Permissions)

    # tool-specific overrides
    claude: ClaudeOverrides = Field(default_factory=ClaudeOverrides)
    gemini: GeminiOverrides = Field(default_factory=GeminiOverrides)
    opencode: OpenCodeOverrides = Field(default_factory=OpenCodeOverrides)


# ── Project Catalog (Level 1 — Static) ──────────────────────────────────────


class KnowledgePoolEntry(BaseModel):
    url: str = ""
    path: str = ""
    type: str = ""


class GitHubRef(BaseModel):
    owner: str
    repo: str


class SlackRef(BaseModel):
    channel: str
    id: str = ""


class RedditRef(BaseModel):
    subreddit: str


class Refs(BaseModel):
    github: list[GitHubRef] = Field(default_factory=list)
    slack: list[SlackRef] = Field(default_factory=list)
    reddit: list[RedditRef] = Field(default_factory=list)


class ProjectRef(BaseModel):
    name: str


class ProjectEntry(BaseModel):
    name: str
    local_path: str
    repo: str = ""
    team: str = ""
    env: dict[str, str] = Field(default_factory=dict)
    upstream: list[ProjectRef] = Field(default_factory=list)
    downstream: list[ProjectRef] = Field(default_factory=list)
    knowledge_pool: list[KnowledgePoolEntry] = Field(default_factory=list)
    refs: Refs = Field(default_factory=Refs)


class ProjectCatalog(BaseModel):
    projects: list[ProjectEntry] = Field(default_factory=list)


# ── Initiative (Level 2 — Dynamic) ──────────────────────────────────────────


class InitiativeProjectRef(BaseModel):
    name: str
    role: str = "peer"
    branches: list[str] = Field(default_factory=list)


class LinkRef(BaseModel):
    url: str
    title: str
    description: str = ""


class Decision(BaseModel):
    date: str
    decision: str
    rationale: str = ""
    by: str = ""


class ReferenceDoc(BaseModel):
    path: str
    title: str


class InitiativeConfig(BaseModel):
    name: str
    description: str = ""
    goal: str = ""
    approach: str = ""
    testing: str = ""
    recommended_skills: list[str] = Field(default_factory=list)
    status: str = "active"
    created: str = ""
    projects: list[InitiativeProjectRef] = Field(default_factory=list)
    links: list[LinkRef] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    reference_docs: list[ReferenceDoc] = Field(default_factory=list)
    # Progress tracking — auto-scanned by `coworker status`
    artifacts: dict[str, list[str]] = Field(default_factory=dict)
    remaining: list[str] = Field(default_factory=list)
