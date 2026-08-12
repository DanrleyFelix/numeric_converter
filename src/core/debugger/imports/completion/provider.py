"""Provide bounded, hierarchical completion for debugger imports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_SOURCE_SUFFIXES = frozenset({".asm", ".s"})


@dataclass(frozen=True)
class ImportCompletion:
    """Describe one relative import candidate shown by the editor."""

    value: str
    is_directory: bool = False


class ImportCompletionProvider:
    """List one directory level without reading or assembling source files."""

    def __init__(self) -> None:
        """Initialize an empty directory metadata cache."""

        self._cache: dict[Path, tuple[int, tuple[tuple[str, bool], ...]]] = {}

    def clear(self) -> None:
        """Discard cached directory entries after the active source changes."""

        self._cache.clear()

    def complete(
        self,
        source_path: Path | None,
        typed_path: str,
    ) -> tuple[ImportCompletion, ...]:
        """Return safe direct children matching ``typed_path``."""

        normalized = typed_path.replace("\\", "/")
        reserved = self._reserved_completion(normalized)
        if source_path is None:
            return reserved
        source = source_path.resolve()
        root = source.parent
        parent_text, separator, leaf = normalized.rpartition("/")
        relative_parent = parent_text if separator else ""
        leaf = leaf if separator else normalized
        directory = self._safe_directory(root, relative_parent)
        if directory is None:
            return reserved
        prefix = f"{relative_parent}/" if relative_parent else ""
        candidates = list(reserved if not relative_parent else ())
        for name, is_directory in self._entries(directory):
            if not name.casefold().startswith(leaf.casefold()):
                continue
            candidate = (directory / name).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                continue
            if candidate == source or (
                not is_directory and candidate.suffix.lower() not in _SOURCE_SUFFIXES
            ):
                continue
            value = f"{prefix}{name}{'/' if is_directory else ''}"
            if value.casefold() != normalized.casefold():
                candidates.append(ImportCompletion(value, is_directory))
        return tuple(
            sorted(
                candidates,
                key=lambda item: (not item.is_directory, item.value.casefold()),
            )
        )

    def _entries(self, directory: Path) -> tuple[tuple[str, bool], ...]:
        """Return cached safe children invalidated by directory mtime."""

        try:
            modified = directory.stat().st_mtime_ns
        except OSError:
            return ()
        cached = self._cache.get(directory)
        if cached is not None and cached[0] == modified:
            return cached[1]
        try:
            entries = tuple(
                (entry.name, entry.is_dir())
                for entry in directory.iterdir()
                if not any(character.isspace() for character in entry.name)
                and (entry.is_dir() or entry.suffix.lower() in _SOURCE_SUFFIXES)
            )
        except OSError:
            entries = ()
        self._cache[directory] = (modified, entries)
        return entries

    @staticmethod
    def _safe_directory(root: Path, relative: str) -> Path | None:
        """Resolve one child directory while rejecting traversal outside root."""

        if Path(relative).is_absolute() or ":" in relative:
            return None
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return None
        return candidate if candidate.is_dir() else None

    @staticmethod
    def _reserved_completion(typed_path: str) -> tuple[ImportCompletion, ...]:
        """Offer the reserved current-file token only at the import root."""

        normalized = typed_path.casefold()
        if (
            "/" not in typed_path
            and "current_file".startswith(normalized)
            and normalized != "current_file"
        ):
            return (ImportCompletion("current_file"),)
        return ()
