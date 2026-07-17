# Claude Code API 兼容性 & SIMPLE 模式

## CLAUDE_CODE_SIMPLE 的副作用

`CLAUDE_CODE_SIMPLE=1` 会禁用以下所有本地功能（不是仅简化 API 调用）：

| 被禁用的功能 | 影响 |
|-------------|------|
| Skills 加载 | `~/.claude/skills/` 和 `.claude/skills/` 全部跳过 |
| CLAUDE.md | 全局和项目级 CLAUDE.md 都不读取 |
| Hooks | UserPromptSubmit、PreToolUse、PostToolUse、Stop 全不触发 |
| MCP Servers | 不自动连接 |
| Session Memory | 不记录 |
| Custom Agents | `.claude/agents/` 不会加载 |

**结论：除非确定需要最简环境，否则不要设 CLAUDE_CODE_SIMPLE=1。**

---

## Claude Code 对非 Anthropic API 的自动降级

当 `ANTHROPIC_BASE_URL` 指向第三方 API（DeepSeek、Z.AI 等）时，Claude Code 会自动检测并降级不兼容的功能。

### Tool Search — 依赖 Anthropic 私有协议

Tool Search 是 Anthropic 的私有扩展，用于延迟加载工具 schema 以节省 context。

```
Tool Search 开启时的流程：

  Claude CLI                      Anthropic API（原生）
      │                                │
      │  请求（只带工具名字，不带 schema）  │
      │ ─────────────────────────────▶ │
      │                                │  模型：我要用 github_create_issue
      │  ◀────── tool_reference ────── │
      │                                │
      │  本地查找 github_create_issue 详情 │
      │                                │
      │  请求（带上完整工具 schema）       │
      │ ─────────────────────────────▶ │
      │                                │  模型生成正确的 tool call
      │  ◀─────── tool_use ─────────── │
```

关键在第 3 步：**Anthropic API 返回 `tool_reference` 类型**（告诉 CLI 去查工具定义），这不是标准 OpenAI 协议的一部分。

DeepSeek / Z.AI 实现的是 OpenAI 兼容协议：
- 认识 `tool_use`（直接调用工具）
- **不认识** `tool_reference`（延迟查工具）← Anthropic 私有扩展

所以 Claude Code 检测到非 Anthropic 主机后，**自动禁用 Tool Search**，避免 API 报错。

> 如果你的代理转发了 `tool_reference` 块，可以设 `ENABLE_TOOL_SEARCH=true` 强制开启。

### Fast Mode — Agent SDK 限制

非 Anthropic 主机或 Agent SDK 模式下自动禁用，不影响功能。

### 不受影响的功能（纯本地）

| 功能 | 为什么兼容 |
|------|-----------|
| Skills | 纯本地读取 `SKILL.md` |
| CLAUDE.md | 纯本地读取项目配置 |
| Hooks | 纯本地执行 shell 脚本 |
| MCP Servers | 纯本地进程通信 |
| Plugins | 纯本地加载 |
| Bash / Read / Write / Grep | 标准协议，所有 API 都支持 |

---

## 推荐配置

```bash
# .zshrc — 不要设 CLAUDE_CODE_SIMPLE
# 让 Claude Code 自己判断哪些需要降级

export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"

# wrapper 函数也去掉 CLAUDE_CODE_SIMPLE
claude-deepseek() {
  ANTHROPIC_API_KEY="$DEEPSEEK_API_KEY" \
  ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic" \
  ANTHROPIC_MODEL="deepseek-v4-pro" \
  command claude "$@"
}
```

### 诊断命令

```bash
# 查看 skills 是否被加载
claude --debug --print "list skills" 2>&1 | grep -i "skill\|reduced\|simple"
```

关键日志行：
- `[reduced mode] Skipping skill dir discovery` ← 说明 SIMPLE 模式在生效
- `getSkills returning: 0 skill dir commands` ← skills 没被加载

### 重要：修改 .zshrc 后必须重新加载

修改 `.zshrc` 后，当前终端不会自动生效。因为 `.zshrc` 只在终端启动时执行一次。

```bash
# 当前终端：手动 source
source ~/.zshrc

# 或者：开一个新终端（自动读取 .zshrc）
```

**不要忘记**：Claude Code session 也是从父终端继承环境变量的。所以：
1. 先 `source ~/.zshrc` 或开新终端
2. 再启动 Claude Code
3. 用 `/reload-skills` 验证 skills 数量

---

## Skill 清理记录

### 2026-07-17 清理

CLEANUP 前：139 skills
CLEANUP 后：~60 skills

| 清理项 | 数量 | 说明 |
|--------|------|------|
| `~/.claude/commands/*.md` | 60 个 | 旧版格式，已迁移到 skills，全部删除 |
| `~/.claude/skills/test-load` | 1 | 调试用临时 skill |
| `~/.claude/skills/hello-skill` | 1 | 测试 skill |
| `~/.claude/skills/my-skills2` | 1 | 空 plugin 模板 |
| `~/.claude/skills/my-skills3` | 1 | 空 plugin 模板 |
| `~/.claude/skills/test-skill` | 1 | 空 plugin 模板 |
| write-doc `.claude-plugin/` | — | 非法 plugin.json 残留 |
| marketplace 缓存 | 29 | `claude-plugins-official` 市场浏览缓存 |

### Skills 来源分布（清理后）

| 来源 | 数量 |
|------|------|
| `~/.claude/skills/` | 36 个 ai-coworker skills |
| `.claude/skills/` | 3 个 project loop skills |
| 已安装 plugins | ~22 个（superpowers 14 + discord 2 + telegram 2 + ...） |

| 2026-07-17 | 初始版本：CLAUDE_CODE_SIMPLE 问题排查 & Tool Search 原理 |
| 2026-07-17 | 补充：source zshrc 步骤、skill 清理记录、最终 skill 来源分布 |
