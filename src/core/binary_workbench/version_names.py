from __future__ import annotations

import re
from collections.abc import Callable
from typing import TypeVar

_VERSION_NAME_PART_RE = re.compile(r"(\d+)")
_T = TypeVar("_T")


def natural_version_key(name: str) -> tuple[object, ...]:
    return tuple(
        int(part) if part.isdigit() else part.casefold()
        for part in _VERSION_NAME_PART_RE.split(name)
        if part
    )


def sorted_versions(
    versions: list[_T],
    *,
    name_of: Callable[[_T], str],
) -> list[_T]:
    return sorted(versions, key=lambda version: natural_version_key(name_of(version)))