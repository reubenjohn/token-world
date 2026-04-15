---
phase: 02-mechanic-framework
reviewed: 2026-04-12T08:19:10Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - src/token_world/mechanic/__init__.py
  - src/token_world/mechanic/protocol.py
  - src/token_world/mechanic/context.py
  - src/token_world/mechanic/engine.py
  - src/token_world/mechanic/loader.py
  - src/token_world/mechanic/matchers.py
  - src/token_world/mechanic/registry.py
  - src/token_world/mechanic/trace.py
  - src/token_world/mechanic/seeds/movement/mechanic.py
  - src/token_world/mechanic/seeds/observation/mechanic.py
  - src/token_world/mechanic/seeds/environmental_reaction/mechanic.py
  - src/token_world/cli.py
  - src/token_world/universe/scaffold.py
  - tests/test_mechanic/conftest.py
  - tests/test_mechanic/test_cli.py
  - tests/test_mechanic/test_engine.py
  - tests/test_mechanic/test_registry.py
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-04-12T08:19:10Z
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

The mechanic framework is well-structured overall. The protocol, context DSL, chain engine, matchers, registry, and trace are cleanly separated. The seed mechanics implement the protocol correctly, and the CLI commands are sensible. No security vulnerabilities or data-loss risks were found.

Three warnings were identified: the `Mechanic` ABC does not enforce required class attributes (`id`, `description`) at definition time, causing obscure `AttributeError` at runtime instead of clear feedback at class definition; the loader selects the first alphabetically-matched subclass without filtering abstract intermediaries; and a bad `mechanic.py` (syntax error, import failure) causes the entire registry scan to abort rather than skip the bad entry.

Four informational items cover private-attribute access, missing error handling for absent git, a redundant test assertion, and absence of module-level caching in the loader.

---

## Warnings

### WR-01: Mechanic ABC does not enforce `id` and `description` class attributes

**File:** `src/token_world/mechanic/protocol.py:29-44`
**Issue:** `id` and `description` are declared as bare class-level annotations on the `Mechanic` ABC with no `abstractmethod`, no `__init_subclass__` check, and no default value. A concrete subclass that omits either attribute instantiates successfully but raises `AttributeError` when the registry accesses `mechanic_cls.id` or `mechanic_cls.description` during scan — producing a confusing error message far from the definition site. Verified experimentally: `NoidMechanic().id` raises `AttributeError: type object 'NoidMechanic' has no attribute 'id'`.

**Fix:** Add `__init_subclass__` to `Mechanic` to validate these attributes at class-definition time:

```python
def __init_subclass__(cls, **kwargs: object) -> None:
    super().__init_subclass__(**kwargs)
    import inspect
    if not inspect.isabstract(cls):
        if not isinstance(getattr(cls, "id", None), str):
            raise TypeError(f"{cls.__name__} must define a string class attribute 'id'")
        if not isinstance(getattr(cls, "description", None), str):
            raise TypeError(f"{cls.__name__} must define a string class attribute 'description'")
```

---

### WR-02: Loader returns first alphabetical subclass without filtering abstract intermediaries

**File:** `src/token_world/mechanic/loader.py:41-48`
**Issue:** The loader scans `dir(module)` and returns the **first** class that is a non-`Mechanic` subclass of `Mechanic`. The check `attr is not Mechanic` does not exclude abstract subclasses (those still missing implementations of `check` or `apply`). If a `mechanic.py` defines an abstract mixin `AbstractBase(Mechanic)` and a concrete `ConcreteImpl(AbstractBase)`, and `AbstractBase` sorts alphabetically before `ConcreteImpl`, the loader returns `AbstractBase`. The registry's `get_mechanic()` then calls `AbstractBase()`, which raises `TypeError: Can't instantiate abstract class`. Verified: `inspect.isabstract(AbstractMiddle)` returns `True` for a class missing one abstract method, yet the loader has no such check.

**Fix:** Add an `inspect.isabstract` guard:

```python
import inspect

for attr_name in dir(module):
    attr = getattr(module, attr_name)
    if (
        inspect.isclass(attr)
        and issubclass(attr, Mechanic)
        and attr is not Mechanic
        and not inspect.isabstract(attr)   # <-- add this
    ):
        return attr
```

---

### WR-03: Registry `scan()` aborts entirely on a single malformed mechanic file

**File:** `src/token_world/mechanic/registry.py:68-111`
**Issue:** `scan()` iterates all subdirectories and calls `load_mechanic_class(entry)` for each. If any `mechanic.py` has a `SyntaxError`, `ImportError`, or runtime exception during module execution, the exception propagates unhandled and aborts the entire scan — leaving the registry index empty. This means one broken generated mechanic renders the entire universe unusable via `list-mechanics` or `run-mechanic`. Verified: creating a `mechanics/bad/mechanic.py` with a syntax error causes `MechanicRegistry(...)` to raise `SyntaxError`.

**Fix:** Wrap the per-entry load in a try/except and log a warning instead of aborting:

```python
import warnings

for entry in sorted(self._mechanics_dir.iterdir()):
    if not entry.is_dir() or not (entry / "mechanic.py").exists():
        continue
    try:
        mechanic_cls = load_mechanic_class(entry)
    except Exception as exc:
        warnings.warn(
            f"Skipping mechanic in '{entry.name}': {exc}",
            stacklevel=2,
        )
        continue
    # ... rest of loop
```

---

## Info

### IN-01: Engine accesses private `ctx._graph` attribute directly

**File:** `src/token_world/mechanic/engine.py:65`
**Issue:** `ChainExecutionEngine.execute()` reaches into `ctx._graph` to pass the raw `KnowledgeGraph` to `_evaluate_chain`. This creates a hidden coupling between `engine.py` and the internal representation of `MechanicContext`. If `MechanicContext` is ever refactored to wrap a different backing store, this access would silently break.

**Fix:** Add a package-internal property to `MechanicContext` (or accept the graph as a separate parameter to `execute`):

```python
# In MechanicContext, add:
@property
def _graph_ref(self) -> KnowledgeGraph:
    """Internal: exposes graph reference for engine use only."""
    return self._graph
```

Then in engine.py line 65 replace `ctx._graph` with `ctx._graph_ref`. Alternatively, restructure `execute()` to accept `graph: KnowledgeGraph` as a separate parameter alongside `ctx`.

---

### IN-02: `scaffold.py` does not handle missing `git` executable

**File:** `src/token_world/universe/scaffold.py:86-104`
**Issue:** `scaffold_universe()` calls `subprocess.run(["git", "init"], check=True, ...)`. If `git` is not installed, this raises `FileNotFoundError` which propagates uncaught through `manager.create()` and the CLI, producing a confusing traceback rather than a clean error message.

**Fix:** Catch `FileNotFoundError` around the git block:

```python
try:
    subprocess.run(["git", "init"], cwd=universe_dir, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=universe_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initialize universe"],
        cwd=universe_dir, check=True, capture_output=True, env=_git_env,
    )
except FileNotFoundError:
    pass  # git not available; universe created without version history
except subprocess.CalledProcessError as exc:
    import warnings
    warnings.warn(f"git init failed for universe '{slug}': {exc.stderr.decode()}")
```

---

### IN-03: Redundant dead condition in test assertion

**File:** `tests/test_mechanic/test_cli.py:73-74`
**Issue:** The assertion reads:
```python
assert "not found" in result.output.lower() or "not found" in (result.output + (result.output or "")).lower()
```
The second operand concatenates `result.output` with `result.output or ""` (which is always `result.output` since it's a non-None string), making it `result.output * 2`. This evaluates identically to the first operand, so the `or` branch is always unreachable dead code.

**Fix:** Simplify to:
```python
assert "not found" in result.output.lower()
```

---

### IN-04: Loader does not cache loaded modules in `sys.modules`

**File:** `src/token_world/mechanic/loader.py:33-39`
**Issue:** `load_mechanic_class()` calls `importlib.util.module_from_spec()` and `spec.loader.exec_module(module)` without registering the module in `sys.modules`. Each call re-executes the module file from scratch. Two consequences: (1) calling `load_mechanic_class()` on the same directory twice returns two distinct class objects with no `isinstance` relationship between them; (2) module-level side effects (e.g., print statements, registrations) execute on every call. In the current codebase this is harmless because the registry calls `load_mechanic_class` once per entry and caches the result in `self._classes`. But if the loader is called independently multiple times (e.g., in tests), class identity is lost.

**Fix:** Register the module in `sys.modules` using its derived name, or document the no-caching behavior explicitly in the docstring so callers know not to rely on class identity across calls:

```python
import sys
# After exec_module:
sys.modules[module_name] = module
```

Note: if two mechanic directories share the same folder name (e.g., in different universes), their module names would collide in `sys.modules`. A scoping prefix (e.g., using the full path hash) would be needed to avoid that collision.

---

_Reviewed: 2026-04-12T08:19:10Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
