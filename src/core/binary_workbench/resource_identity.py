from __future__ import annotations

from pathlib import Path


def file_resource_identifiers(path: Path | None, display_name: str = "") -> list[str]:
    names: list[str] = []
    if path is not None:
        resolved = path.resolve()
        names.append(f"path:{str(resolved).lower()}")
        names.append(f"directory:{str(resolved.parent).lower()}")
        names.append(f"name:{path.name.lower()}")
    elif display_name:
        names.append(f"name:{display_name.lower()}")
    return _unique(names)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
