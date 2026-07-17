# Changelog

## 2026-07-14 — Dashboard全面重写 (Loop build)

### 新增/重写页面
1. **Overview** — Stat卡片可点击跳转到对应子页面 (Sessions/Tools/Skills/Knowledge)，Daily Sessions可切换 7d/14d/30d/90d/180d/365d
2. **Projects** — 完整重写，worktree路径合并 (例 `-home-cicidi-project-ai-coworker` → `ai-coworker`)，unknown→"root"，每个project可展开查看session列表
3. **Sessions** — 改为可展开列表，显示具体时间/duration/root project，展开后显示message timeline(用户prompt/AI响应/tool call)
4. **Models** — 替换Monitor页面，显示token用量/费用/model breakdown/请求性能
5. **Skills** — 显示version/body size，按last N days筛选，展开显示call timeline/trigger type/session id/SKILL.md内容/调用它的project列表
6. **Tools** — 类似Skills结构，展开显示call timeline/session使用情况
7. **Files** — 4个filter输入框(name/type/project/initiative)，显示branch列，展开显示read/write timeline/by tool/skill
8. **Knowledge** — 全新结构: project/initiative/model/创建时间/session id，内容分四栏: 做什么项目/问题与重试/可复用经验/避免什么

### DB Schema变更
- `session_stats` 新增: `tokens_input`, `tokens_output`, `cost`, `turn_count`

### Import变更
- OpenCode: `cost`, `tokens_input`, `tokens_output` 现在写入到SQLite
- Claude JSONL: 根据消息内容长度估算token用量

### 新增API Endpoints
- `GET /api/projects` — 项目聚合 (含worktree合并)
- `GET /api/models` — 模型用量/token/cost
- `GET /api/daily-sessions?days=N` — 可配置时间范围的daily sessions
- `GET /api/tool-sessions?tool=X` — 使用特定tool的sessions
- `GET /api/skill-detail?name=X&days=N` — skill调用详情
- `GET /api/skill-timeline?name=X&days=N` — skill时间线
- `GET /api/tool-detail?tool=X` — tool详情
- `GET /api/file-detail` — 文件操作详情 (含filter参数)
- `GET /api/sessions/{id}/messages` — session消息列表

## 2026-07-08 — Polish Loop (autonomous, manager + deepseek worker + QA gate)

### Pipeline validated
- Manager(glm) → worker(deepseek-v4-pro) → tester(pytest) → reviewer(glm) → push. Worktree-isolated, never touches master.

### Fixes
- **B1**: fix 3 failing `tests/python/test_state_update.py` tests. Root cause: `tests/python/test_skill_frontmatter.py::test_scaffold_conforms` used a raw `os.chdir(tmp)` (never restored) → process cwd pointed at a deleted `TemporaryDirectory` → subsequent `monkeypatch.chdir` raised `FileNotFoundError: os.getcwd()`. Switched to the `monkeypatch` fixture. Suite: **167 passed, 0 failed** (was 3 failed, 164 passed). Branch `fix/b1-state-update-tests`.
- **S1**: removed root `static/` (assets already moved into `src/coworker/dashboard/static/`); `.gitignore` added `.coworker/`, `*.bak`, `docs/work-review/`, `docs/superpowers/`, `.polish-loop-stop`.

## 2026-06-24 — Review & Testing Update

### Fixes
- Fixed broken references in CLAUDE.md to non-existent `templates/team-common/` paths

### Tests
- Added `tests/python/test_cli.py` — 11 CLI tests (version, status, help, project list, config validation, skill references)
- Added `tests/python/test_skill_factory_integration.py` — 11 integration tests (source repo validation, deploy consistency, CLAUDE.md references)
- All 33+ existing tests still pass; 22 new tests added

### Documentation
- Updated README with testing instructions and skill management workflow
