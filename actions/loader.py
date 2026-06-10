from __future__ import annotations

from importlib import util
from pathlib import Path

from core.text import normalize_text


def discover_actions(action_root: Path) -> list[dict]:
    actions: list[dict] = []
    if not action_root.exists():
        return actions

    for file_path in sorted(action_root.glob("*.py")):
        if file_path.name.startswith("_") or file_path.stem in {"__init__", "base", "loader"}:
            continue

        module = _load_module(file_path)
        if module is None:
            continue

        triggers = [normalize_text(trigger) for trigger in getattr(module, "TRIGGERS", [])]
        run = getattr(module, "run", None)
        if not triggers or not callable(run):
            continue

        actions.append(
            {
                "name": getattr(module, "ACTION_NAME", file_path.stem),
                "triggers": triggers,
                "run": run,
                "path": file_path,
            }
        )

    return actions


def _load_module(file_path: Path):
    try:
        spec = util.spec_from_file_location(file_path.stem, file_path)
        if spec is None or spec.loader is None:
            return None
        module = util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None
