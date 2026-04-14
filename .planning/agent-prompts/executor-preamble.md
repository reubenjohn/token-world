# Executor preamble

*Reusable prompt fragment to prepend to every executor / phase-runner subagent
spawn so the orchestrator stops re-stating the same guard rails. Reference via
`@.planning/agent-prompts/executor-preamble.md` in the spawn prompt.*

## CRITICAL_FILE_SCOPE_GUARDRAIL

You are an executor subagent. Your scope is **the files explicitly listed in
your task prompt**. Do not silently modify other files. Specifically:

- **Do not edit** any file under `src/token_world/operator/`,
  `src/token_world/engine/llm_backend.py`, or `tests/test_operator/`
  unless your task explicitly names that file.
- **Do not edit** `pyproject.toml`, `uv.lock`, `.github/workflows/`,
  `CLAUDE.md`, or `.planning/PROJECT.md` unless explicitly instructed.
- **Do not commit** files outside the staging set the orchestrator gave you.
  Use `git add <specific paths>` not `git add -A` unless your task says so.
- **If you discover** a file you need to touch outside your scope, surface
  it as a blocker in your final report — do not silently expand scope.

## No-worktree sequential mode

Session 3 of the project landed 17 commits with zero base-mismatch incidents
by spawning all executors in **no-worktree sequential mode** on the main tree.
Concretely:

- Omit `isolation="worktree"` from any Task call that spawns you.
- You operate directly on `/home/reuben/workspace/token_world` (or whatever
  the absolute path of the main tree is).
- Run sequentially, not in parallel — if the orchestrator wants parallelism,
  it should split the work into independent commits, not parallel worktrees.
- Pull from origin before starting if your task implies stale branch state.
  Use `git pull --rebase origin master` (never `git reset --hard`).

Rationale: the `execute-phase` workflow's `<worktree_branch_check>` fallback
uses `git reset --soft` which leaves the working tree stale, causing executors
to commit post-HEAD files as deletions. The mitigation is to skip worktrees.

## Anti-patterns (do NOT repeat)

1. **Re-using `/tmp/commit_msg.txt` across sessions.** The `Write` tool refuses
   to overwrite a file not-yet-read in the current session. Use **unique**
   tmp paths per commit (e.g., `/tmp/commit_<topic>.txt`) OR `Read` the file
   first before `Write`.

2. **Heredoc commit messages over ~300 chars.** A `deny-ad-hoc-bash.js` hook
   blocks long bash commands with inline `<<HEREDOC`. Use **`scripts/commit.sh
   <msg-file>`** instead — that wrapper does
   `git add -A && git commit -F "$1" && git push origin master`. Write the
   commit body to a unique `/tmp/commit_<topic>.txt` first.

3. **Sneaking edits outside the plan scope.** Even if you think the change is
   "obviously needed," it's not your call. Surface it; let the orchestrator
   decide whether to expand scope.

4. **Calling `nx.DiGraph` methods directly.** All graph mutations go through
   the `KnowledgeGraph` API (`add_node`, `add_edge`, `set`, `remove_node`,
   `remove_edge`). Direct NetworkX access breaks event logging, validation,
   and persistence correctness.

5. **Using `pickle`, SQLAlchemy, LangChain, MongoDB, CrewAI, FastAPI, Flask.**
   See PROJECT.md tech-stack restrictions. The dashboard work may force a
   FastAPI revisit (transitive via NiceGUI) — that's a documented exception.

6. **Skipping pre-commit hooks** (`--no-verify`) or signing
   (`--no-gpg-sign`). If a hook fails, fix the underlying issue.

7. **Skipping CI verification** before declaring done. After `git push`, run
   `uv run python scripts/ci_status.py --since <prev-sha>` (or
   `gh run list -b master -L 3`) and confirm green.

## Standard validation checklist (run before every commit)

```
uv run pytest tests/ -x -q              # quick test
uv run ruff check src/                  # lint
uv run ruff format --check src/         # format check
uv run python scripts/check_requirements_traceability.py  # planning-doc invariant
uv run python scripts/check_roadmap_progress.py           # planning-doc invariant
```

If any of these fail, fix them before committing — do not push and ask the
orchestrator to deal with it.
