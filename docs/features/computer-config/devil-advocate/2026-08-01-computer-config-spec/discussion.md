# Adversarial Review — computer-config-spec.md

- **Date**: 2026-08-01
- **Document under review**: `docs/computer-config/spec/computer-config-spec.md`
- **Review type**: devil-advocate (con/pro/judge debate, max 5 rounds)
- **Status**: complete (1 round, then manual verification)

## Metadata

- Reviewer: walter-worker-devil-advocate skill
- Model: DeepSeek/deepseek-v4-pro (via CCR)
- Round limit: 5

## Round Log

### Round 1 (2026-08-01)

Con → Pro → Judge. Judge rulings: 9 total, 8 con-wins, 1 pro-wins, 0 deferred.

**Consensus findings:**
1. **Model ID contradiction** — settings.json `model` field hex-decodes to
   `DeepSeek/deepseek-v4-flash`, but 3 env vars say `deepseek-v4-pro`. Spec
   claims v4-pro throughout. Independently VERIFIED by reviewer (see below).
2. Spec section 2.2 says 11 top-level keys, actual is 10.
3. Spec section 4.1 says .tmux.conf 34 lines, actual is 36.
4. Spec section 2.2 says 12 plugins, actual is 13 (12 enabled + 1 disabled semgrep).
5. `_write_json_atomic` name-dropped 3× with no mechanism specified.
6. Manifest format for uninstall unspecified (word appears 8×, zero schema).
7. Inline Benjamin Blue detection algorithm undefined.
8. 0/1/2 single-choice menu contradicts PRD US-4 "one-click install".

**Rulings:**
| Claim | Ruling | Reason |
|-------|--------|--------|
| DeepSeek 1M context, 5x Claude | pro-wins | Math correct, matches live statusline detection code |
| Cost ~17x cheaper | con-wins | Model ID suggests flash ($0.28), making it ~53x; ambiguity unresolved |
| 12 plugins | con-wins | Live has 13 (12 enabled + 1 disabled) |
| .tmux.conf 34 lines | con-wins | Actual 36 |
| Atomic writes via _write_json_atomic | con-wins | Pattern undefined; json.dump non-atomic |
| Uninstall manifest-driven safe | con-wins | No schema; cross-project manifest conflict with walter-worker |
| Inline color detection | con-wins | Algorithm undefined; safety gate unimplementable |
| 0/1/2 menu | con-wins | Contradicts PRD US-4 |

**Unresolved (deferred):**
- Which model actually routes through CCR (flash vs pro)? — cascades into cost/context claims
- Cross-project manifest conflict (walter-worker walks ~/.claude/ recursively)
- Impl-plan Step B1 "remove tmux tracking" may be a phantom task
- Statusline behavior when CCR is down
- Test plan gaps (rollback, missing deps at runtime, non-BB colors, concurrent installs)

### Reviewer verification (post-round)

Independently verified the most impactful finding:
- `model` field hex-decode → `DeepSeek/deepseek-v4-flash` ✅ CONFIRMED
- `env.ANTHROPIC_MODEL` → `DeepSeek/deepseek-v4-pro` ✅ CONFIRMED (contradiction real)
- Top-level keys = 10 (not 11) ✅ CONFIRMED
- enabledPlugins = 13 (not 12) ✅ CONFIRMED
- .tmux.conf = 36 lines (not 34) ✅ CONFIRMED
