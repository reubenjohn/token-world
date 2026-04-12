> **SUPERSEDED:** This research was conducted when Claude Code SDK was the planned agent framework. The project now uses a hybrid approach (Agent SDK at operator layer + raw Anthropic API inside tools). Session persistence is handled by custom JSONL persistence within the universe folder, not the Claude Code SDK's built-in sessions. This document is retained as historical reference only.

# Claude Code SDK Session Management - Research

**Researched:** 2026-04-11
**Domain:** Claude Agent SDK session persistence, JSONL format, rollback/revert for simulation snapshots
**Confidence:** HIGH (verified against official docs + local filesystem inspection)

## Summary

The Claude Agent SDK (formerly `@anthropic-ai/claude-code`, now `@anthropic-ai/claude-agent-sdk` in TS / `claude-agent-sdk` in Python) provides robust session management with JSONL-based persistence. Sessions can be resumed by ID, forked to create branches, and files can be rewound to checkpoints. However, **there is no official API to truncate or revert a session's conversation history to an earlier point** -- the SDK only supports rewinding *file changes*, not the conversation itself.

For Token World's simulation rollback use case, the most viable approaches are:
1. **Fork-based branching** -- at each simulation snapshot, record the session ID; to roll back, fork from that session ID with a new prompt
2. **Direct JSONL truncation** -- manually truncate the JSONL file to a known line offset (unsupported but technically feasible)
3. **Session-per-step** -- start a fresh session per simulation step, injecting prior context via the prompt

**Primary recommendation:** Use fork-based branching (approach 1) as the primary strategy. Each simulation graph node stores its session ID. Rolling back means forking from the snapshot's session ID rather than truncating files. This uses only supported SDK APIs and avoids fragile file manipulation.

## Session Storage Architecture

### File Locations

| Location | Purpose | Format |
|----------|---------|--------|
| `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl` | Conversation transcript | JSONL (one JSON object per line) |
| `~/.claude/projects/<encoded-cwd>/<session-id>/subagents/agent-<id>.jsonl` | Subagent transcripts | JSONL |
| `~/.claude/projects/<encoded-cwd>/<session-id>/tool-results/` | Large tool outputs | Text files |
| `~/.claude/sessions/<pid>.json` | Active process registry | JSON (pid, sessionId, cwd, startedAt) |

[VERIFIED: local filesystem inspection on this machine]

The `<encoded-cwd>` is the absolute working directory with every non-alphanumeric character replaced by `-`. For example, `/home/reuben/workspace/token_world` becomes `-home-reuben-workspace-token-world`. [CITED: code.claude.com/docs/en/agent-sdk/sessions]

### JSONL Line Format

Each line in the JSONL file is a self-contained JSON object. The conversation forms a linked list via `parentUuid` fields. Observed line types from local file inspection:

| `type` field | Description | Key fields |
|-------------|-------------|------------|
| `queue-operation` | Session queue management (enqueue/dequeue) | `operation`, `timestamp`, `sessionId` |
| `user` | User message (prompt or tool result) | `uuid`, `parentUuid`, `message.role`, `message.content`, `timestamp`, `isSidechain`, `cwd`, `sessionId` |
| `assistant` | Assistant response (text, tool_use, thinking) | `uuid`, `parentUuid`, `message.role`, `message.content`, `timestamp`, `isSidechain` |
| `file-history-snapshot` | File state checkpoint marker | (metadata only) |
| `ai-title` | Auto-generated session title | (metadata only) |

[VERIFIED: parsed actual JSONL files from ~/.claude/projects/-home-reuben-workspace-token-world/]

**Linked list structure:** Every `user` and `assistant` message has a `uuid` and `parentUuid`. The first message has `parentUuid: null`. Each subsequent message points to the previous one. This forms a single chain (or tree when forked).

**Sidechain flag:** `isSidechain: true` marks subagent messages. These are stored in separate subagent JSONL files under `<session-id>/subagents/`.

### Example JSONL line (user message):
```json
{
  "parentUuid": "95726a13-dedc-4962-a958-df43d6fa84da",
  "isSidechain": false,
  "type": "user",
  "message": {
    "role": "user",
    "content": [{"type": "text", "text": "..."}]
  },
  "uuid": "5bfc490f-ec16-4a46-8572-50d6c825f6ca",
  "timestamp": "2026-04-11T22:47:55.740Z",
  "userType": "external",
  "entrypoint": "claude-vscode",
  "cwd": "/home/reuben/workspace/token_world",
  "sessionId": "d54adfe4-82c5-4880-bd53-a4aa25befff2",
  "version": "2.1.86",
  "gitBranch": "master"
}
```

## SDK Session APIs (Python)

### Installation
```bash
pip install claude-agent-sdk
```
Current installed version: 0.1.58 [VERIFIED: pip show on this machine]
NPM package `@anthropic-ai/claude-agent-sdk` version: 0.2.101 [VERIFIED: npm view]

### Core Session Operations

#### Creating a session (standalone query)
```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

async def run():
    session_id = None
    async for message in query(
        prompt="Analyze the auth module",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Glob", "Grep"],
        ),
    ):
        if isinstance(message, ResultMessage):
            session_id = message.session_id
    return session_id
```
[CITED: code.claude.com/docs/en/agent-sdk/sessions]

#### Resuming a session by ID
```python
async for message in query(
    prompt="Continue from where we left off",
    options=ClaudeAgentOptions(
        resume=session_id,  # UUID string
        allowed_tools=["Read", "Edit", "Write"],
    ),
):
    ...
```
[CITED: code.claude.com/docs/en/agent-sdk/sessions]

#### Forking a session (branch without mutating original)
```python
forked_id = None
async for message in query(
    prompt="Try a different approach",
    options=ClaudeAgentOptions(
        resume=session_id,
        fork_session=True,  # Creates new session with copy of history
    ),
):
    if isinstance(message, ResultMessage):
        forked_id = message.session_id  # New session ID, original unchanged
```
[CITED: code.claude.com/docs/en/agent-sdk/sessions]

#### Multi-turn with ClaudeSDKClient (automatic session tracking)
```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

async with ClaudeSDKClient(options=ClaudeAgentOptions(...)) as client:
    await client.query("First question")
    async for msg in client.receive_response():
        ...
    # Second query automatically continues same session
    await client.query("Follow-up question")
    async for msg in client.receive_response():
        ...
```
[CITED: code.claude.com/docs/en/agent-sdk/sessions]

### Session Inspection APIs

```python
from claude_agent_sdk import list_sessions, get_session_messages, get_session_info

# List sessions for a directory
sessions = list_sessions(directory="/path/to/project", limit=10)
for s in sessions:
    print(f"{s.session_id}: {s.summary} ({s.file_size} bytes)")

# Get messages from a session (supports pagination)
messages = get_session_messages(
    session_id="uuid-here",
    directory="/path/to/project",
    limit=50,
    offset=0
)
for m in messages:
    print(f"type={m.type}, uuid={m.uuid}")

# Get session metadata
info = get_session_info(session_id="uuid-here", directory="/path/to/project")
```
[VERIFIED: tested locally with actual sessions, imports confirmed working]

**SessionMessage fields:** `type` ("user"/"assistant"), `uuid`, `session_id`, `message` (dict with role/content), `parent_tool_use_id`

**SDKSessionInfo fields:** `session_id`, `summary`, `last_modified`, `file_size`, `custom_title`, `first_prompt`, `git_branch`, `cwd`, `tag`, `created_at`

### File Checkpointing (rewind file changes, NOT conversation)

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, UserMessage, ResultMessage

options = ClaudeAgentOptions(
    enable_file_checkpointing=True,
    permission_mode="acceptEdits",
    extra_args={"replay-user-messages": None},  # Required for checkpoint UUIDs
)

checkpoint_id = None
session_id = None

async with ClaudeSDKClient(options) as client:
    await client.query("Refactor the module")
    async for message in client.receive_response():
        if isinstance(message, UserMessage) and message.uuid and not checkpoint_id:
            checkpoint_id = message.uuid  # First user msg UUID = restore point
        if isinstance(message, ResultMessage):
            session_id = message.session_id

# Later: rewind files (NOT conversation) to checkpoint
async with ClaudeSDKClient(
    ClaudeAgentOptions(enable_file_checkpointing=True, resume=session_id)
) as client:
    await client.query("")  # Empty prompt to open connection
    async for message in client.receive_response():
        await client.rewind_files(checkpoint_id)
        break
```
[CITED: code.claude.com/docs/en/agent-sdk/file-checkpointing]

**Critical distinction:** `rewind_files()` restores *files on disk* to their state at a checkpoint. It does NOT rewind the conversation history. The agent still remembers everything that happened.

## Rollback Strategies for Simulation Engine

### Strategy 1: Fork-Based Branching (RECOMMENDED)

**How it works:**
1. At each simulation graph node, store the `session_id` from `ResultMessage`
2. When simulation rolls back to node N, use `fork_session=True` with node N's session_id
3. The agent gets full context up to node N but starts a fresh branch

**Pros:**
- Uses only supported SDK APIs
- Original session preserved (can try multiple rollback paths)
- Agent has full conversational context from the snapshot point

**Cons:**
- Creates a new JSONL file per fork (disk usage grows)
- Cannot remove "knowledge" the agent gained -- it still has the full conversation up to the fork point
- Each fork is a full copy of history (no deduplication)

**Implementation sketch:**
```python
class AgentSessionManager:
    def __init__(self):
        self.snapshots: dict[str, str] = {}  # graph_node_id -> session_id

    async def run_step(self, prompt: str, graph_node_id: str, parent_node_id: str | None = None):
        options = ClaudeAgentOptions(
            allowed_tools=["Read", "Edit", "Write"],
        )

        if parent_node_id and parent_node_id in self.snapshots:
            # Continue from parent's session
            options.resume = self.snapshots[parent_node_id]

        session_id = None
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                session_id = message.session_id

        self.snapshots[graph_node_id] = session_id
        return session_id

    async def rollback_to(self, graph_node_id: str, new_prompt: str) -> str:
        """Fork from a previous snapshot point."""
        parent_session = self.snapshots[graph_node_id]

        new_session_id = None
        async for message in query(
            prompt=new_prompt,
            options=ClaudeAgentOptions(
                resume=parent_session,
                fork_session=True,
            ),
        ):
            if isinstance(message, ResultMessage):
                new_session_id = message.session_id

        return new_session_id
```

### Strategy 2: Direct JSONL Truncation (UNSUPPORTED BUT FEASIBLE)

**How it works:**
1. Before each simulation step, record the line count of the JSONL file
2. To rollback, truncate the file to the recorded line count
3. Resume the session -- the SDK should pick up the truncated history

**Pros:**
- True state revert (agent literally loses memory of future events)
- No disk bloat from fork copies
- Simple conceptually

**Cons:**
- **Completely unsupported** -- SDK may cache state in memory, have checksums, or behave unpredictably
- Must handle `parentUuid` chain integrity (truncation must occur at a clean boundary)
- Metadata lines (`file-history-snapshot`, `ai-title`, `queue-operation`) interspersed with conversation lines
- Subagent files in subdirectories would also need truncation
- Risk of corruption if SDK writes additional metadata on resume

**Implementation sketch (use at your own risk):**
```python
import os

class JNOLTruncator:
    def __init__(self, session_dir: str, session_id: str):
        self.jsonl_path = os.path.join(session_dir, f"{session_id}.jsonl")

    def get_line_count(self) -> int:
        with open(self.jsonl_path) as f:
            return sum(1 for _ in f)

    def get_message_uuid_at_line(self, line_num: int) -> str | None:
        """Get the UUID of the message at a specific line."""
        import json
        with open(self.jsonl_path) as f:
            for i, line in enumerate(f):
                if i == line_num:
                    data = json.loads(line)
                    return data.get('uuid')
        return None

    def truncate_to_line(self, target_line: int):
        """Truncate JSONL file to first N lines."""
        lines = []
        with open(self.jsonl_path) as f:
            for i, line in enumerate(f):
                if i >= target_line:
                    break
                lines.append(line)
        with open(self.jsonl_path, 'w') as f:
            f.writelines(lines)
```

**WARNING:** This approach has not been tested against the SDK's resume logic. The SDK may reject or silently create a new session if it detects inconsistencies. [ASSUMED]

### Strategy 3: Session-Per-Step with Context Injection

**How it works:**
1. Each simulation step creates a fresh session
2. Relevant context from prior steps is injected into the prompt
3. Rollback simply means not injecting context beyond the snapshot point

**Pros:**
- Cleanest separation -- no session manipulation needed
- Each step is fully independent and reproducible
- Easy to serialize/deserialize simulation state

**Cons:**
- Agent loses nuanced conversational context (only gets what you explicitly inject)
- Higher token cost (re-injecting context every step)
- Must carefully design the context injection format

### Strategy Comparison

| Property | Fork-Based | JSONL Truncation | Session-Per-Step |
|----------|-----------|------------------|------------------|
| SDK Support | Official | Unsupported | Official |
| Agent Context Quality | Full | Full (if it works) | Partial (injected only) |
| Disk Usage | High (copies) | Low | Medium |
| Rollback Fidelity | Good (fork point) | Perfect (exact state) | Depends on injection |
| Risk | Low | High | Low |
| Complexity | Low | Medium | Medium |

## Key Facts and Constraints

1. **Python always persists sessions to disk.** There is no `persistSession: false` equivalent in the Python SDK. TypeScript has this option. [CITED: code.claude.com/docs/en/agent-sdk/sessions]

2. **`cwd` must match for resume.** If your simulation runner's working directory changes, the SDK won't find the session file. [CITED: code.claude.com/docs/en/agent-sdk/sessions]

3. **File checkpointing != conversation checkpointing.** `rewind_files()` only reverts file changes on disk. The conversation history stays intact. The agent still "remembers" everything. [CITED: code.claude.com/docs/en/agent-sdk/file-checkpointing]

4. **Fork creates a full copy.** There's no copy-on-write or deduplication. Each fork duplicates the entire conversation history into a new JSONL file. [ASSUMED -- based on JSONL being plain append-only files]

5. **Subagent sessions are nested.** When using the Agent tool (subagents), their sessions are stored in `<session-id>/subagents/agent-<id>.jsonl`. Rollback must account for these. [VERIFIED: local filesystem inspection]

6. **The JSONL format is append-only in normal operation.** New messages are appended as new lines. The SDK does not modify existing lines. [VERIFIED: observed file structure; CITED: known bug report about rewrites github.com/anthropics/claude-code/issues/5034]

7. **Session IDs are UUIDs.** Format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`. [VERIFIED: local files]

8. **`get_session_messages()` supports pagination.** `limit` and `offset` parameters let you read subsets of the conversation. [CITED: code.claude.com/docs/en/agent-sdk/python]

## Common Pitfalls

### Pitfall 1: CWD Mismatch on Resume
**What goes wrong:** Resume silently creates a new session instead of continuing the old one.
**Why:** Sessions are stored under `<encoded-cwd>`. If you resume from a different working directory, the SDK looks in the wrong folder.
**How to avoid:** Always pass the same `cwd` in `ClaudeAgentOptions` that was used when the session was created.
[CITED: code.claude.com/docs/en/agent-sdk/sessions]

### Pitfall 2: Confusing File Rewind with Conversation Rewind
**What goes wrong:** You call `rewind_files()` expecting the agent to forget what happened. It doesn't -- it still has full conversational context.
**Why:** File checkpointing only tracks filesystem changes via Write/Edit/NotebookEdit. The conversation JSONL is untouched.
**How to avoid:** For conversation rollback, use fork (or JSONL truncation at your own risk). For file rollback, use checkpointing.
[CITED: code.claude.com/docs/en/agent-sdk/file-checkpointing]

### Pitfall 3: Disk Bloat from Aggressive Forking
**What goes wrong:** Each fork copies the full history. In a simulation with many rollbacks, disk usage grows linearly.
**How to avoid:** Implement a cleanup strategy -- delete old forked sessions that are no longer reachable in the simulation graph. Use `list_sessions()` and file deletion.

### Pitfall 4: Python SDK Version Mismatch
**What goes wrong:** API functions missing or behaving differently.
**Why:** The SDK was recently renamed from `claude-code-sdk` to `claude-agent-sdk`. Old tutorials reference the wrong package.
**How to avoid:** Use `pip install claude-agent-sdk` (not `claude-code-sdk`). Current version: 0.1.58.
[VERIFIED: pip show on this machine]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Fork creates a full copy of JSONL (no deduplication) | Key Facts #4 | If there's deduplication, disk bloat concern is reduced |
| A2 | JSONL truncation would be accepted by SDK resume logic | Strategy 2 | If SDK rejects truncated files, Strategy 2 is unviable |
| A3 | No SDK-level conversation rollback API exists | Summary | If such an API exists undocumented, it would be the ideal solution |

## Open Questions

1. **Does the SDK validate JSONL integrity on resume?**
   - What we know: The SDK reads the JSONL to reconstruct conversation history
   - What's unclear: Whether it checksums the file, validates parentUuid chains, or checks expected message counts
   - Recommendation: Test JSONL truncation experimentally on a non-critical session before relying on Strategy 2

2. **How large do forked session files get in practice?**
   - What we know: Each fork copies full history; observed files are 200KB-600KB for moderate sessions
   - What's unclear: Growth rate under heavy simulation use (hundreds of fork points)
   - Recommendation: Estimate based on average tokens per step * number of steps * number of forks

3. **Can `system_prompt` inject enough context to make Strategy 3 viable?**
   - What we know: `ClaudeAgentOptions.system_prompt` accepts a string; prompts can include structured context
   - What's unclear: How much prior simulation state can be packed into a prompt before quality degrades
   - Recommendation: Prototype with a 3-step simulation and compare agent quality across strategies

4. **Is there a way to disable session persistence in Python?**
   - What we know: Docs say "Python always persists to disk"
   - What's unclear: Whether undocumented options exist, or whether we can use a tmpdir as cwd
   - Recommendation: If disk usage is a concern, use a tmpdir and clean up manually

## Sources

### Primary (HIGH confidence)
- [Claude Agent SDK - Work with sessions](https://code.claude.com/docs/en/agent-sdk/sessions) - session management, resume, fork, continue APIs
- [Claude Agent SDK - File checkpointing](https://code.claude.com/docs/en/agent-sdk/file-checkpointing) - rewind_files, checkpoint UUIDs
- [Claude Agent SDK - Python reference](https://code.claude.com/docs/en/agent-sdk/python) - ClaudeAgentOptions, query(), ClaudeSDKClient, session functions
- Local filesystem inspection of `~/.claude/projects/` JSONL files and `~/.claude/sessions/` registry

### Secondary (MEDIUM confidence)
- [PyPI: claude-agent-sdk](https://pypi.org/project/claude-agent-sdk/) - package metadata
- [GitHub: anthropics/claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python) - source code, issues
- [GitHub issue #5034: Duplicate entries in JSONL](https://github.com/anthropics/claude-code/issues/5034) - JSONL write behavior

### Tertiary (LOW confidence)
- [GitHub issue #555: Resume creates new session](https://github.com/anthropics/claude-agent-sdk-python/issues/555) - edge case with resume

## Metadata

**Confidence breakdown:**
- Session storage format: HIGH - verified via local file inspection + official docs
- SDK APIs (Python): HIGH - tested imports and function calls locally
- Rollback strategies: MEDIUM - Strategy 1 (fork) is well-documented; Strategy 2 (truncation) is untested speculation
- JSONL integrity on truncation: LOW - no evidence either way

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (SDK is actively evolving; check for new session management APIs)
