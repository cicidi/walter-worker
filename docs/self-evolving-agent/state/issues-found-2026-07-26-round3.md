# Issues Found — 2026-07-26 (Round 3)

> 🔍 甲方质检 (find-issues) — Security + Test Coverage Audit

## Security Findings (3 found)

| ID | Source | Issue | Fix | Priority |
|----|--------|-------|-----|----------|
| SEC-1 | [Checkmarx](https://checkmarx.com/learn/ai-security/claude-code-security-top-6-risks-controls-and-best-practices/) — Claude Code auto-loads .env files | No `.claudeignore` file exists. Claude Code could read `.env` contents into context and transmit to API. | Create `.claudeignore` with `.env`, `*.pem`, `*.key`, `credentials/`, `secrets.yaml` | **CRITICAL** |
| SEC-2 | [Agent Security Best Practices](https://github.com/rohitg00/awesome-claude-code-toolkit/blob/main/rules/security.md) — PostToolUse secret scanning | Our PostToolUse hooks (`coworker memory sync`) extract lessons but NEVER scan for leaked secrets in tool output | Add PostToolUse secret-scan hook that checks for API key patterns in tool results | HIGH |
| SEC-3 | [Credential Proxy Pattern](https://github.com/pleasedodisturb/llm-safe-haven/blob/main/docs/credential-management.md) — env vars visible to agent | `os.environ.get("DEEPSEEK_API_KEY")` used directly in 3 places (llm.py, mem0_client.py, cli.py). Agent can read via `env` command. | Add `.claudeignore` deny rules for shell env reads. Document credential proxy as future enhancement. | MEDIUM |

## Test Coverage Gaps (7 found)

| ID | Module | Issue | Priority |
|----|--------|-------|----------|
| T-1 | `errors.py` | 18 error codes defined — ZERO tests | HIGH |
| T-2 | `metrics.py` | Evolution metrics collection — ZERO tests | HIGH |
| T-3 | `train.py` | Batch training pipeline — ZERO tests | HIGH |
| T-4 | `validate.py` | Claude SDK validation harness — ZERO tests | MEDIUM |
| T-5 | `wrong_history.py` | Wrong-history injection — ZERO tests (auto-worker injects it but never verifies injection worked) | MEDIUM |
| T-6 | `autoworker/rules.py` | 8 validation rules — ZERO tests (old test file was rewritten) | MEDIUM |
| T-7 | `autoworker/state.py` | State file management — ZERO tests (old test file was rewritten) | MEDIUM |

## Code Deep-Dive (2 found)

| ID | File:Line | Issue | Fix | Priority |
|----|-----------|-------|-----|----------|
| C-6 | src/coworker/cli.py:1184 | `--task-file` parameter reads arbitrary files from user input — no path validation | Add `click.Path(exists=True)` validation | LOW |
| C-7 | src/coworker/memory/llm.py:33 | `FALLBACK_CHAIN` hardcodes model names — if DeepSeek deprecates `deepseek-v4-flash` again, all extraction fails | Read model list from env var `COWORKER_LLM_MODELS` as override | LOW |

## DeepSeek Analysis — Top 5 This Round

1. **[CRITICAL] No .claudeignore** — This is a security hole. Claude Code reads `.env` files into context. One compromised MCP server or malicious README could exfiltrate all API keys.

2. **[HIGH] 7 modules without tests** — Total test debt is growing. errors.py (18 error codes), metrics.py (7 metrics), train.py (batch pipeline) all untested. A bug in any of these is undetectable.

3. **[HIGH] No secret scanning hooks** — Every tool call that reads a file could leak a secret. PostToolUse should scan results for API key patterns.

4. **[MEDIUM] Agent can read env vars** — `os.environ.get("DEEPSEEK_API_KEY")` is called in plain Python. If an agent runs `import os; print(os.environ)`, all keys are exposed.

5. **[LOW] Hardcoded model names** — If DeepSeek changes model names again (as happened with `deepseek-chat`), fallback chain breaks silently.

## Summary

| Priority | Count | Auto-Fixable |
|----------|-------|-------------|
| CRITICAL | 1 | 1 (.claudeignore) |
| HIGH | 5 | 3 (test stubs for errors/metrics/train) |
| MEDIUM | 4 | 2 (wrong_history test, rules test) |
| LOW | 2 | 2 (path validation, model env override) |
| **Total (new)** | **12** | **8 auto-fixable** |
| **Grand Total** | **32** | **21 fixed/auto-fixable** |
