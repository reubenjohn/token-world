---
phase: 00-universe-infrastructure
reviewed: 2026-04-11T12:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - pyproject.toml
  - src/token_world/cli.py
  - src/token_world/mcp_server.py
  - src/token_world/models.py
  - src/token_world/universe/__init__.py
  - src/token_world/universe/manager.py
  - src/token_world/universe/paths.py
  - src/token_world/universe/scaffold.py
  - src/token_world/universe/templates/__init__.py
  - src/token_world/universe/templates/claude_md.py
  - src/token_world/universe/templates/mcp_config.py
  - tests/conftest.py
  - tests/test_mcp_server.py
  - tests/test_universe/__init__.py
  - tests/test_universe/test_manager.py
  - tests/test_universe/test_paths.py
  - tests/test_universe/test_scaffold.py
findings:
  critical: 1
  warning: 2
  info: 1
  total: 4
status: issues_found
---

# Phase 0: Code Review Report

**Reviewed:** 2026-04-11T12:00:00Z
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Phase 0 implements universe infrastructure: CLI (Click), Pydantic models, XDG path resolution, universe lifecycle management (create/load/list/delete), folder scaffolding with git init, a stub MCP JSON-RPC server, and comprehensive tests. The code is well-structured with clear separation of concerns, good docstrings, proper type annotations, and solid test coverage.

One security issue was found in the `UniverseManager.load()` method which lacks path traversal protection. Two warnings relate to silent error swallowing in metadata loading and an incorrect JSON-RPC notification handling pattern in the MCP server. Overall the codebase is clean and well-organized for a Phase 0 foundation.

## Critical Issues

### CR-01: Path traversal in UniverseManager.load()

**File:** `src/token_world/universe/manager.py:59`
**Issue:** The `load()` method constructs a filesystem path from an untrusted `slug` parameter (`self.data_dir / slug`) without validating that the resolved path remains under `data_dir`. A slug like `../../etc` resolves to `/etc`, allowing callers to confirm the existence of arbitrary directories on the filesystem. The `delete()` method has a containment check on line 73 (`path.resolve().relative_to(self.data_dir.resolve())`), but `load()` does not. Since `load()` is a public method and is called from `delete()` as a precursor, the asymmetry means `load()` alone is vulnerable. The `create()` path is safe because `slugify()` strips dots and slashes.
**Fix:**
Add the same containment check used in `delete()` to `load()`. Better yet, extract it into a shared helper:
```python
def _resolve_universe_path(self, slug: str) -> Path:
    """Resolve and validate a universe path from a slug.

    Raises:
        FileNotFoundError: If no universe with the given slug exists.
        ValueError: If path traversal is detected.
    """
    path = self.data_dir / slug
    # Security: verify resolved path is under data_dir (T-00-02)
    try:
        path.resolve().relative_to(self.data_dir.resolve())
    except ValueError:
        raise ValueError(f"Invalid slug: path traversal detected in '{slug}'")
    if not path.exists() or not (path / "universe.db").exists():
        raise FileNotFoundError(f"Universe '{slug}' not found")
    return path

def load(self, slug: str) -> Path:
    return self._resolve_universe_path(slug)

def delete(self, slug: str) -> None:
    path = self._resolve_universe_path(slug)
    shutil.rmtree(path)
```

## Warnings

### WR-01: Silent error swallowing in _load_metadata

**File:** `src/token_world/universe/manager.py:112`
**Issue:** The `_load_metadata` method catches `(sqlite3.Error, KeyError)` and returns `None` with no logging or warning. This means corrupted universe databases or schema mismatches cause universes to silently disappear from `list()` output. A user who has a universe with a corrupted database would see it vanish from `token-world list` with no diagnostic information, making the problem very difficult to troubleshoot.
**Fix:**
Add logging when metadata loading fails. The project already depends on `loguru`:
```python
from loguru import logger

def _load_metadata(self, universe_dir: Path) -> UniverseMetadata | None:
    db_path = universe_dir / "universe.db"
    try:
        with sqlite3.connect(str(db_path)) as conn:
            rows = conn.execute("SELECT key, value FROM metadata").fetchall()
            data = dict(rows)
            return UniverseMetadata(
                name=data["display_name"],
                slug=data["slug"],
                created_at=datetime.fromisoformat(data["created_at"]),
                schema_version=int(data.get("schema_version", "1")),
            )
    except (sqlite3.Error, KeyError) as e:
        logger.warning(f"Failed to load metadata from {db_path}: {e}")
        return None
```

### WR-02: MCP server sends error responses to notifications

**File:** `src/token_world/mcp_server.py:107-111`
**Issue:** When a JSON-RPC request has no `id` field (i.e., it is a notification), the server should not send any response per the JSON-RPC 2.0 specification. The code correctly handles `notifications/initialized` by returning `None`, but any other notification (a request without an `id`) falls through to the method-not-found error handler on line 107, which sends a response with `"id": None`. Per JSON-RPC 2.0 section 4.1: "The Server MUST NOT reply to a Notification." Sending an error response to a notification violates the protocol and could confuse compliant clients.
**Fix:**
Check for the absence of `id` early and return `None` for all notifications:
```python
def handle_request(request: dict) -> dict | None:
    method = request.get("method", "")
    req_id = request.get("id")

    # JSON-RPC notifications have no "id" -- never respond
    if req_id is None and "id" not in request:
        return None

    # ... rest of method handling ...
```
Note: The check uses both `req_id is None` and `"id" not in request` to distinguish between "no id field" (notification) and "id field explicitly set to null" (which is technically a request with id=null per JSON-RPC).

## Info

### IN-01: Unused `TOOLS` import reference in test assertions

**File:** `tests/test_mcp_server.py:5`
**Issue:** The `TOOLS` constant is imported but only used in the `TestToolsConstant` class (lines 100-114). The other test classes re-discover tools through `handle_request` calls. This is not wrong, but the `TestToolsConstant` tests duplicate assertions already covered by `TestHandleToolsList` (e.g., both verify 4 tools exist, both check tool names). Minor test duplication.
**Fix:** Consider whether `TestToolsConstant` adds value beyond `TestHandleToolsList`. If it tests the constant independently of the handler (which it does), it is fine to keep. No action required unless test maintenance becomes a concern.

---

_Reviewed: 2026-04-11T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
