"""Dynamic mechanic loading from flat Python modules (D-10).

Per Phase 4 D-10 the repository switched from folder-per-mechanic
(`mechanics/<id>/mechanic.py` plus `meta.yaml`) to flat module layout
(`mechanics/<id>.py`). This module provides the discovery primitives the
registry uses to walk a universe's `mechanics/` directory.

Two public helpers:

* :func:`discover_mechanic_modules` -- list ``<id>.py`` files while skipping
  ``__init__.py`` and underscore-prefixed helpers (``_helpers.py`` etc.).
* :func:`load_mechanic_classes` -- import one module and return every
  :class:`Mechanic` subclass it defines (filtering out re-exported bases
  from other modules via ``attr.__module__ == module_name``).
"""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

from token_world.mechanic.protocol import Mechanic


def discover_mechanic_modules(mechanics_dir: Path) -> list[Path]:
    """Return a sorted list of mechanic module files in *mechanics_dir*.

    A mechanic module is any file whose name ends with ``.py`` and does NOT
    start with ``_`` (covers both ``__init__.py`` and helper files such as
    ``_helpers.py``). The filter matches D-05 + D-10:

    * Flat modules only -- subdirectories are ignored.
    * Underscore-prefixed files are registry-invisible helpers.
    * ``__init__.py`` is always skipped (already covered by underscore rule
      but we check explicitly for clarity).

    Args:
        mechanics_dir: The directory to scan.

    Returns:
        Sorted list of candidate module paths. Empty list if the directory
        does not exist.
    """
    if not mechanics_dir.is_dir():
        return []
    modules: list[Path] = []
    for entry in sorted(mechanics_dir.iterdir()):
        if not entry.is_file():
            continue
        if entry.suffix != ".py":
            continue
        if entry.name == "__init__.py":
            continue
        if entry.name.startswith("_"):
            continue
        modules.append(entry)
    return modules


def load_mechanic_classes(module_path: Path) -> list[type[Mechanic]]:
    """Import a mechanic module and return every :class:`Mechanic` subclass.

    The module is loaded via :func:`importlib.util.spec_from_file_location`
    using a deterministic module name of ``"mechanic_<stem>"``. Only classes
    *defined in this module* (``attr.__module__ == module_name``) are
    returned -- this prevents re-detection of :class:`Mechanic` or other
    imported bases that happen to be in-scope at the module level.

    An empty return list is NOT an error: multi-class modules, helper
    modules, and modules pending a subclass all produce ``[]``. Callers
    (currently :class:`MechanicRegistry`) may treat ``[]`` as a validation
    concern but this loader always succeeds when the file imports cleanly.

    Args:
        module_path: Path to a ``.py`` file.

    Returns:
        List of ``Mechanic`` subclasses defined in the module. May be empty.

    Raises:
        FileNotFoundError: If *module_path* does not exist.
        ImportError: If the module fails to load (syntax error, bad import).
    """
    if not module_path.exists():
        raise FileNotFoundError(f"Mechanic module not found: {module_path}")

    module_name = f"mechanic_{module_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec for {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    classes: list[type[Mechanic]] = []
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if not inspect.isclass(attr):
            continue
        if attr is Mechanic or not issubclass(attr, Mechanic):
            continue
        # Filter out Mechanic subclasses imported from elsewhere; only
        # return classes defined in this file. This keeps authoring clean
        # (you can `from ... import SomeBase` without it being indexed).
        if getattr(attr, "__module__", None) != module_name:
            continue
        classes.append(attr)
    return classes
