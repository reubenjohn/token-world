"""Dynamic mechanic loading from folder structure."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

from token_world.mechanic.protocol import Mechanic


def load_mechanic_class(mechanic_dir: Path) -> type[Mechanic]:
    """Dynamically import and return the Mechanic subclass from a mechanic folder.

    Looks for ``mechanic.py`` in the given directory, loads it via importlib,
    and returns the first class that is a concrete subclass of
    :class:`~token_world.mechanic.protocol.Mechanic`.

    Args:
        mechanic_dir: Path to the mechanic folder (must contain ``mechanic.py``).

    Returns:
        The Mechanic subclass found in the module.

    Raises:
        FileNotFoundError: If ``mechanic.py`` does not exist in *mechanic_dir*.
        ValueError: If no Mechanic subclass is found in the module.
    """
    mechanic_file = mechanic_dir / "mechanic.py"
    if not mechanic_file.exists():
        raise FileNotFoundError(f"mechanic.py not found in {mechanic_dir}")

    module_name = f"mechanic_{mechanic_dir.name}"
    spec = importlib.util.spec_from_file_location(module_name, mechanic_file)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot create module spec for {mechanic_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if inspect.isclass(attr) and issubclass(attr, Mechanic) and attr is not Mechanic:
            return attr

    raise ValueError(f"No Mechanic subclass found in {mechanic_file}")
