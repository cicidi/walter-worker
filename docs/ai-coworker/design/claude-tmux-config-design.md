# claude-tmux-config — 独立项目设计文档

**日期**: 2026-08-01
**状态**: 待审阅
**涉及项目**:
- 新建 `claude-tmux-config`（独立仓库，个人 Claude Code + tmux 外观层）
- `ai-coworker`（剥离外观层，保留核心框架）

---

## 1. 背景与动机

用户的 Claude Code 状态栏（`statusline-command.sh`、`wrap-statusline.py`）和
tmux 定制（`.tmux.conf` Benjamin Blue 主题、`~/.tmux/scripts/`）目前**散落在
home 目录下，未被任何 git 仓库跟踪，无版本控制**。同时 ai-coworker 的安装脚本
（`setup/install.sh` Step 16 + `setup/status_info.sh`）会部署一套简单的 tmux
外观，污染所有安装 ai-coworker 的用户。

**目标**:
1. 新建独立项目 `claude-tmux-config`，收拢所有个人 Claude + tmux 外观资产，
   自带安装确认脚本，**对其他用户零影响**。
2. 从 ai-coworker 剥离外观层，使其成为纯框架（context/skills/analytics），
   **不再触碰任何用户终端皮肤**。

---

## 2. 现状盘点（已验证事实）

### 2.1 散落资产（claude-tmux-config 要收拢的）

| 资产 | 当前位置 | 状态 |
|------|---------|------|
| `statusline-command.sh` | `~/.claude/statusline-command.sh` (16KB, live) | 未被 git 跟踪 |
| `wrap-statusline.py` | `~/.claude/wrap-statusline.py` (3.3KB, live) | 未被 git 跟踪 |
| `status_info.sh` | `~/.tmux/scripts/status_info.sh` (303B, 简单版) | 未被 git 跟踪 |
| `benjamin-blue.tmux` 主题段 | `.tmux.conf` 内联 (live) | `.tmux.conf` 未被 git 跟踪 |
| `claude-tmux` binding | `.tmux.conf` `bind-key C-c display-popup` | 第三方 Rust 二进制 |

**注意**: 用户当前实际运行的 `status_info.sh` 是 303B 简单版（仅显示文件夹
路径）。ai-coworker 仓库里的 3KB 富版**从未部署**到用户机器。已确认以简单版为准。

### 2.2 statusline-command.sh 硬编码路径（需参数化）

```
:150  turn_counter_file="$HOME/.claude/turn-counter-${session_id}.json"
:199  cache_file="$HOME/.claude/ccusage-cache.json"
:370  printf ... | python3 ~/.claude/wrap-statusline.py
```

依赖: `jq`、`bc`、`python3`、`git`、`tmux`（`ccusage` 可选，失败优雅降级）。
含 Linux 专属命令 `stat -c %W`、`hostname -s`（macOS 不兼容，暂声明 Linux-only）。

### 2.3 ai-coworker 外观层（要剥离的）

| 位置 | 内容 |
|------|------|
| `setup/install.sh` Step 16 | 部署 tmux 状态栏 + 追加灰白主题到 `.tmux.conf` |
| `setup/status_info.sh` | tmux 富版状态栏脚本 |

### 2.4 ai-coworker 核心层（保留，不受影响）

| 位置 | 内容 |
|------|------|
| `src/coworker/adapters/claude.py` | sync()：permissions/hooks/skills/MCP；inject_*：context 注入 |
| `setup/install.sh` Step 14 | analytics hooks 配置 |
| `coworker *` CLI | 所有命令 |

---

## 3. 目标架构

### 3.1 claude-tmux-config 仓库结构

```
claude-tmux-config/
├── README.md                     # 用途、安装、卸载、截图
├── install.sh                    # 主安装脚本（含确认提示）
├── uninstall.sh                  # 卸载（manifest 驱动）
├── assets/
│   ├── statusline-command.sh     # Claude Code 状态栏（3 处路径参数化）
│   ├── wrap-statusline.py        # ANSI 换行助手（原样）
│   ├── status_info.sh            # tmux 状态栏（简单版，用户现状）
│   └── benjamin-blue.tmux        # tmux 主题文件（独立可 source）
└── docs/
    └── claude-tmux.md            # claude-tmux binding 文档（不自动装二进制）
```

### 3.2 部署目标（与 ai-coworker 完全隔离）

| 资产 | 部署到 |
|------|--------|
| `statusline-command.sh` | `~/.claude/statusline/statusline-command.sh` |
| `wrap-statusline.py` | `~/.claude/statusline/wrap-statusline.py` |
| `status_info.sh` | `~/.tmux/scripts/status_info.sh` |
| `benjamin-blue.tmux` | `~/.tmux/conf.d/benjamin-blue.tmux` |
| settings.json `statusLine` | `~/.claude/settings.json` |

---

## 4. 安装与确认机制

复用 ai-coworker install.sh 的交互风格（0/1/2 菜单 + 显式 y/N 确认，默认 N）：

```
claude-tmux-config install
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 安装哪些定制？(默认跳过，无破坏)
  1) Claude Code 状态栏 (statusline + statusLine 设置)
  2) tmux 主题 + 状态栏 (Benjamin Blue + source theme)
  0) 跳过
选择 [0]:
```

- **组件 1**: 检查 `jq`/`bc`/`python3` → 部署 statusline-command.sh +
  wrap-statusline.py → inline python 合并 `statusLine` 到 settings.json
  （沿用 ai-coworker Step 14 的 `_merge` 模式，幂等）
- **组件 2**: 部署 `~/.tmux/conf.d/benjamin-blue.tmux` → 在 `.tmux.conf` 末尾
  `source`（幂等检查：`grep -q "benjamin-blue.tmux"`）
- 每个组件独立 `y/N` 确认，默认 N（保守）。

**⚠️ 用户已有内联配色特例**: 用户自己的 `.tmux.conf` 已内联 Benjamin Blue 配色。
install 检测到已有内联配色时，**只部署 status_info.sh，不重复加 source**，
避免污染现有文件。全新用户则用完整 theme 文件。

---

## 5. 幂等与安全

- **settings.json**: 备份 `.bak` + 原子写入（复用 `_write_json_atomic` 模式）
- **.tmux.conf**: 改动前备份 `~/.tmux.conf.bak`；marker 检查防重复追加
- **卸载** (`uninstall.sh`): manifest 驱动，移除 statusLine、删除
  `~/.tmux/conf.d/`、还原 `.tmux.conf` 里的 source 行

---

## 6. ai-coworker 剥离方案

### 6.1 从 ai-coworker 移除

| 移除项 | 位置 | 影响 |
|--------|------|------|
| Step 16 tmux 部署 | `setup/install.sh` | 不再触碰任何用户 `.tmux.conf` / `~/.tmux/` |
| `setup/status_info.sh`（富版） | 删除文件 | 从未部署到用户机器，无回归 |
| manifest 里 tmux 相关 | install.sh manifest walker | 不追踪 tmux |

### 6.2 ai-coworker 保留（不受影响）

- hooks / permissions / skills / MCP / context injection
- analytics（Step 14 hooks）
- 所有 `coworker *` CLI

### 6.3 受影响测试需同步更新

`tests/conftest.py`、`tests/setup/test_install.bats`、`tests/setup/test_update.bats`、
`tests/analytics/test_install.py`、`tests/analytics/test_data.py`

---

## 7. 明确不做的事

- ❌ 不自动安装 `claude-tmux` Rust 二进制（第三方依赖，仅文档化 binding）
- ❌ 不移植 `git_branch.sh`（冗余，简单版 status_info.sh 已满足现状）
- ❌ 不把设计文档硬塞进 ai-coworker 的 setup/（它是独立项目）
- ❌ 不做 macOS 适配（`stat -c %W` / `hostname -s` 为 Linux 专属，暂声明 Linux-only）

---

## 8. 风险与缓解

| 风险 | 缓解 |
|------|------|
| statusline-command.sh 性能开销 | ccusage 缓存 (120s TTL)、git 命令轻量、整体 <100ms |
| 缺失 jq/bc/python3 静默失败 | install 时 `command -v` 检查并 warn |
| .tmux.conf 被污染 | 幂等 marker + 改动前备份 `.bak` |
| settings.json 中断损坏 | `_write_json_atomic`（temp + rename + .bak） |
| 跨平台 (macOS) 不兼容 | 声明 Linux-only |
| 卸载留孤儿文件 | manifest 追踪新路径 + owned_dirs 扩展 |

---

## 9. 验收标准

1. `claude-tmux-config` 仓库创建成功，assets 完整、路径参数化
2. `install.sh` 运行：0/1/2 菜单 + y/N 确认，默认 N
3. 安装后：`~/.claude/statusline/` 两个文件就位，settings.json 有 `statusLine`
4. 安装后：`~/.tmux/conf.d/benjamin-blue.tmux` 就位（或检测到已有配色跳过）
5. `uninstall.sh` 干净移除所有痕迹
6. ai-coworker 剥离后：install.sh 不再触碰 tmux，核心功能测试全绿
