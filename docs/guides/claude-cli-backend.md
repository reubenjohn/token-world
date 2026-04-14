# `claude-cli` LLM Backend — Zero-Cost UAT via Your Claude Subscription

> **Orientation:** This guide describes a Phase 07.1 feature. For project-wide conventions see [`CLAUDE.md`](../../CLAUDE.md) and [`PROJECT.md`](../../PROJECT.md). For system architecture, see [`docs/design/architecture.md`](../design/architecture.md).
>
> **Last updated:** 2026-04-14

## TL;DR

Token World's LLM calls normally go through the raw Anthropic SDK and cost real API dollars. Phase 07.1 adds a pluggable backend that routes every simulation LLM call (classifier, observer, resident agent) through the `claude` CLI subprocess instead — which uses your existing Claude subscription at **zero marginal cost**. To turn it on, set one env var:

```bash
export TOKEN_WORLD_BACKEND=claude-cli
```

Now `token-world playtest`, `token-world agent-turn`, and anything else driving the simulation will use `claude -p` under the hood. No code changes, no config files, no CLI flags.

## When to Use It

This backend is tailored for hobbyists who want to run the Phase 6 UAT playtests (or any LLM-driven simulation loop) without paying for API calls.

**Use `claude-cli` when:**
- You have the `claude` CLI installed and are logged in with an active Claude subscription
- You're running live UAT, end-to-end playtests, or exploratory agent-turn sessions
- You don't need fine-grained token/cost telemetry (CLI doesn't expose token counts)
- Latency of 10-15s per call is acceptable (a 5-turn playtest takes ~3 min)

**Stick with the default SDK backend when:**
- You're running automated CI / regression suites (unit tests inject fakes anyway, so env var is irrelevant)
- You need accurate token usage reporting for cost analysis
- You need streaming (neither backend streams — this is a general limitation, not CLI-specific)
- You're hitting your subscription rate limits during heavy use

## Setup

### Prerequisites

1. **`claude` CLI on `PATH`** — verify with `which claude` (should print a path). If missing, install per the Claude Code docs.
2. **Logged in** — `claude` CLI must have an active session. Run any `claude -p "hello"` interactively once to verify.

### Turn it on

```bash
export TOKEN_WORLD_BACKEND=claude-cli
```

Add to your shell profile (`~/.zshrc`, `~/.bashrc`) if you want it persistent.

### Verify

```bash
uv run python -c "from token_world.engine import get_backend; b = get_backend(); print(type(b).__name__)"
```

Expected output:

```
ClaudeCLIBackend
```

Without the env var set (or with any other value), the same command prints `AnthropicSDKBackend`.

## Running UAT

All three Phase 6 UAT items close in under 5 minutes total with this backend. Commands below are copy-pasteable — they were executed verbatim on 2026-04-14 to close the v1.0 milestone.

### UAT 1 — End-to-end playtest with live LLM

```bash
export TOKEN_WORLD_BACKEND=claude-cli
token-world playtest uatworld --turns 5 --no-operator --output /tmp/uat1_report.json
```

**Expected:** 5 turns complete in ~30 seconds. The report file contains personality-driven action text, a composite score, and 3 prompt hashes. Sample agent text from the 2026-04-14 run:

```
*glances over shoulder*

This UATWorld is cold. Empty. Too empty. Feels like a freshly wiped
partition—no artifacts, no footprints, no tell-tale fragment...
```

### UAT 2 — Prompt-hash regression trigger

Modify any simulation prompt (add a trailing space to `classifier.py`'s `_SYSTEM_PROMPT`) and rerun:

```bash
token-world playtest uatworld --turns 3 --no-operator
```

**Expected:** stdout reports

```
Prompt change detected in: ['classifier_system_prompt']. Triggering regression...
```

and `<universe>/regression-history.jsonl` gains an entry like:

```json
{"trigger": "prompt_hash_change", "changed_prompts": ["classifier_system_prompt"], "exit_code": 1, ...}
```

Revert the prompt change and run `scripts/update_prompt_hashes.py <slug>` to restore the baseline.

### UAT 3 — Sonnet judge pass

```bash
token-world playtest uatworld --turns 3 --no-operator --judge --output /tmp/uat3_report.json
```

**Expected:** the report's `judge` block contains `model: "claude-sonnet-4-5"`, numeric scores in `[0.0, 1.0]` for coherence / personality_consistency / world_rule_adherence, and a prose rationale.

Inspect with:

```bash
uv run python scripts/inspect_playtest_report.py /tmp/uat3_report.json
```

## Model IDs — What Works and What Doesn't

The `claude` CLI's model resolver is strict. Per locked decision **D-04**, the backend passes your model string through verbatim — no alias translation. Token World's `_MODEL` constants already use full IDs, so this is transparent to normal users.

**Works:**

```bash
claude --model claude-haiku-4-5-20251001 -p "test"    # classifier default
claude --model claude-sonnet-4-5 -p "test"            # observer / judge default
```

**Fails:**

```bash
claude --model haiku-4-5 -p "test"    # ERROR: model alias unknown
claude --model haiku -p "test"        # Works, but resolves to older model
```

If you're adding a new model constant in the codebase, use the full dated ID and validate it with `claude --model <id> -p "ping"` once before wiring it up.

## What You Give Up

Per locked decisions **D-07** and **D-09**:

| Feature | SDK backend | CLI backend |
|---|---|---|
| Token usage (`input_tokens`, `output_tokens`) | Exact from `resp.usage` | Best-effort: `(words_in + words_out) × 1.3` estimate |
| Cost telemetry | Real dollars computed | Reported as `$0.00 (via CLI subscription)` |
| Latency per call | ~2-4s | ~10-15s (median ~12s) |
| Streaming | No (neither backend streams) | No |
| Session/memory passthrough | N/A (stateless at backend layer) | No — every call is a fresh `-p` invocation |
| Rate-limit recovery | SDK retry logic | Inherits your Claude subscription limits; failures re-raise |

The `TickSummaryWriter` and `TurnScorer` cost fields in CLI-backend playtests will always show `$0.00`. Token counters in Observer (`last_input_tokens`, `last_output_tokens`) stay at 0 on the CLI path (the word-count estimate is documented in D-07 but not wired in v1).

## Architecture (Brief)

```
simulation caller (Classifier / Observer / ResidentAgent)
            |
            v
     LLMBackend (Protocol)
            |
   +--------+--------+
   |                 |
   v                 v
AnthropicSDKBackend   ClaudeCLIBackend
   |                 |
   v                 v
anthropic.messages   subprocess.run(
  .create(...)         ["claude", "--model", <id>, "-p", <prompt>],
                       timeout=120, check=True, capture_output=True, text=True
                     )
```

Three pieces make this work:

1. **`LLMBackend` Protocol** — one method, `call(*, model, system, prompt, max_tokens) -> str`. Both implementations return clean plain text; callers never see wrapper objects or fences. (D-01)
2. **`AnthropicSDKBackend`** — wraps an injected `anthropic.Anthropic` client. This is the default path and matches pre-Phase-07.1 behaviour.
3. **`ClaudeCLIBackend`** — synchronous `subprocess.run` (D-09) with a 120s timeout (D-05, 8x safety margin over the observed ~15s median). Strips leading/trailing Markdown fences from `stdout` because the CLI wraps JSON in ` ```json ` fences even when the prompt forbids it (D-03). Does **not** use `shutil.which` — relies on `claude` being on `PATH` (D-06).

Dispatch is environment-variable driven: `get_backend()` reads `TOKEN_WORLD_BACKEND`, returns `ClaudeCLIBackend()` if it equals `claude-cli` (case-insensitive, whitespace-stripped), else lazy-imports `anthropic.Anthropic` and returns an SDK-wrapped default. The lazy import preserves the Phase 5 pattern of no module-load SDK instantiation so tests can patch cleanly.

## Reverting

To go back to the SDK path:

```bash
unset TOKEN_WORLD_BACKEND
```

Or set it to anything that isn't `claude-cli`:

```bash
export TOKEN_WORLD_BACKEND=anthropic-sdk    # any other value = SDK
```

No code changes needed. The SDK path requires `ANTHROPIC_API_KEY` to be set and billable.

## Troubleshooting

### `FileNotFoundError: [Errno 2] No such file or directory: 'claude'`

The `claude` CLI is not on `PATH`. Install it or update your shell's `PATH`. Verify with `which claude`.

### `subprocess.CalledProcessError: Command '[...]' returned non-zero exit status N`

The `claude` CLI exited with an error. Common causes:

- **Wrong model ID** — check stderr in the exception. If it says "model may not exist", you're probably using an alias (e.g., `haiku-4-5`) instead of the full ID (`claude-haiku-4-5-20251001`). See the model IDs section above.
- **Not logged in** — run `claude -p "test"` interactively once to re-authenticate.
- **Rate limit / subscription exhausted** — Claude subscriptions have usage caps. The CalledProcessError will propagate up to the classifier/observer, which have their own retry logic (classifier retries up to 3× on ValidationError; observer has its darkness fallback). If you consistently hit this, revert to the SDK backend or wait for your subscription window to reset.

### `subprocess.TimeoutExpired` after 120 seconds

A single `claude -p` call exceeded the 120s timeout. Normal median is ~12s, so a 120s timeout is an 8x safety margin. If you hit this regularly, something is wrong upstream (network, CLI hang, unusually huge prompt). The exception propagates; callers' retry logic handles it.

### The backend isn't being used

Verify the env var is actually set in the shell where you're invoking `token-world`:

```bash
echo "$TOKEN_WORLD_BACKEND"
uv run python -c "from token_world.engine import get_backend; print(type(get_backend()).__name__)"
```

If `echo` is empty, your `export` didn't persist to this shell session. If the Python check still prints `AnthropicSDKBackend` despite `echo` showing `claude-cli`, check for typos — the match is case-insensitive but the string must be exactly `claude-cli` (hyphen, not underscore).

### `anthropic` SDK not installed but I only want CLI

Fine — the `anthropic` import is lazy inside `get_backend()`. As long as you set `TOKEN_WORLD_BACKEND=claude-cli`, the SDK is never touched. (Unit tests that inject fakes also work without a real SDK install.)

## Related Files & Code Pointers

- [`src/token_world/engine/llm_backend.py`](../../src/token_world/engine/llm_backend.py) — the whole module (147 lines)
  - `LLMBackend` Protocol — line 36
  - `_strip_markdown_fences()` helper — line 47
  - `AnthropicSDKBackend` — line 71
  - `ClaudeCLIBackend` — line 96
  - `get_backend()` factory — line 129
- [`src/token_world/engine/classifier.py`](../../src/token_world/engine/classifier.py) — consumes `LLMBackend` via `backend` field + `__post_init__` wrap-or-default
- [`src/token_world/engine/observer.py`](../../src/token_world/engine/observer.py) — consumes via Observer-local `_UsageCapturingSDKBackend` subclass (preserves D-24 token telemetry on SDK path)
- [`src/token_world/resident/agent.py`](../../src/token_world/resident/agent.py) — consumes via `backend=` kwarg; `run_turn()` flattens message history to a single prompt string
- [`tests/test_engine/test_llm_backend.py`](../../tests/test_engine/test_llm_backend.py) — 29 unit tests (Protocol, factory, fence stripping, subprocess mocking)
- [`tests/test_engine/test_llm_backend_integration.py`](../../tests/test_engine/test_llm_backend_integration.py) — 13 end-to-end tests proving `TOKEN_WORLD_BACKEND=claude-cli` threads through all three LLM-calling classes
- [`.planning/phases/07.1-claude-cli-llm-backend-zero-cost-live-playtesting-via-user-s/07.1-CONTEXT.md`](../../.planning/phases/07.1-claude-cli-llm-backend-zero-cost-live-playtesting-via-user-s/07.1-CONTEXT.md) — full design rationale, D-01 through D-10
- [`.planning/phases/06-resident-agent-end-to-end-loop/06-VERIFICATION.md`](../../.planning/phases/06-resident-agent-end-to-end-loop/06-VERIFICATION.md) — Live UAT Results section (evidence that all 3 UAT items passed via this backend on 2026-04-14)
