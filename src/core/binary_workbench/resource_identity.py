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


def matching_file_identifiers(
    saved: list[str],
    path: Path | None,
    display_name: str = "",
) -> bool:
    current = set(file_resource_identifiers(path, display_name))
    saved_set = set(saved)
    saved_paths = {value for value in saved_set if value.startswith("path:")}
    if saved_paths:
        return bool(current.intersection(saved_paths))
    return bool(current.intersection(saved_set))


def merged_file_identifiers(current: list[str], extra: list[str]) -> list[str]:
    return _unique([*current, *extra])


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
