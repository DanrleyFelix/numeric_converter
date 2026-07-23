from __future__ import annotations

from pathlib import Path

from src.modules.utils import read_json, write_json
from src.presentation.repository.debugger_window.state import DebuggerWindowState


class DebuggerWindowStateRepository:
    """Store debugger geometry by workspace without changing workspace manifests."""

    def __init__(self, path: Path) -> None:
        """Bind the repository to its independent JSON state file."""

        self._path = path

    def load(self, workspace_key: str) -> DebuggerWindowState:
        """Load one workspace state while tolerating absent or legacy values."""

        payload = read_json(self._path)
        raw = payload.get(workspace_key) if isinstance(payload, dict) else None
        if not isinstance(raw, dict):
            return DebuggerWindowState()
        return DebuggerWindowState(
            x=_optional_int(raw.get("x")),
            y=_optional_int(raw.get("y")),
            width=_positive_int(raw.get("width")),
            height=_positive_int(raw.get("height")),
            maximized=bool(raw.get("maximized", False)),
            horizontal_sizes=_sizes(raw.get("horizontal_sizes")),
            vertical_sizes=_sizes(raw.get("vertical_sizes")),
            bottom_tab=max(0, _optional_int(raw.get("bottom_tab")) or 0),
        )

    def save(self, workspace_key: str, state: DebuggerWindowState) -> None:
        """Persist one workspace state while preserving all other entries."""

        payload = read_json(self._path)
        values = dict(payload) if isinstance(payload, dict) else {}
        values[workspace_key] = state.payload()
        write_json(self._path, values)


def _optional_int(value: object) -> int | None:
    """Return an integer value without accepting booleans."""

    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _positive_int(value: object) -> int:
    """Return a positive stored dimension or zero."""

    parsed = _optional_int(value)
    return parsed if parsed is not None and parsed > 0 else 0


def _sizes(value: object) -> tuple[int, ...]:
    """Normalize a persisted splitter-size sequence."""

    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, int) and item >= 0)

