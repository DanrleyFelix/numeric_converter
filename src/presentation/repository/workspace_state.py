import json
from pathlib import Path
from typing import Any

from src.application.dto.application_state import (
    ApplicationContextDTO,
    CommandContextDTO,
    ConverterStateDTO,
    WorkspaceStateDTO,
)
from src.application.dto.command_entry import CommandEntryDTO


def _converter_fields(raw: dict[str, Any]) -> dict[str, str]:
    fields = {
        "decimal": "",
        "binary": "",
        "hexBE": "",
        "hexLE": "",
    }
    for key in fields:
        value = raw.get(key, "")
        fields[key] = "" if value is None else str(value)
    return fields


def _context_from_payload(payload: dict[str, Any]) -> ApplicationContextDTO:
    converter_raw = payload.get("converter", {})
    command_raw = payload.get("command", {})

    return ApplicationContextDTO(
        converter=ConverterStateDTO(
            from_type=converter_raw.get("from_type", "decimal"),
            fields=_converter_fields(converter_raw.get("fields", {})),
            message=converter_raw.get("message"),
        ),
        command=CommandContextDTO(
            active_line=command_raw.get("active_line", ""),
            history=[
                CommandEntryDTO(
                    input=item.get("input", ""),
                    output=item.get("output"),
                )
                for item in command_raw.get("history", [])
            ],
            instructions=list(command_raw.get("instructions", [])),
            variables=dict(command_raw.get("variables", {"ANS": 0})),
            workspace_view_mode=command_raw.get("workspace_view_mode", "variables"),
        ),
        key_panel_visible=payload.get("key_panel_visible", True),
    )


def _context_to_payload(context: ApplicationContextDTO) -> dict[str, Any]:
    return {
        "converter": {
            "from_type": context.converter.from_type,
            "fields": _converter_fields(context.converter.fields),
            "message": context.converter.message,
        },
        "command": {
            "active_line": context.command.active_line,
            "history": [
                {"input": entry.input, "output": entry.output}
                for entry in context.command.history
            ],
            "instructions": list(context.command.instructions),
            "variables": dict(context.command.variables),
            "workspace_view_mode": context.command.workspace_view_mode,
        },
        "key_panel_visible": context.key_panel_visible,
    }


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


class ApplicationContextRepository:

    def __init__(self, root: Path):
        self._directory = root / "data" / "contexts"
        self._directory.mkdir(parents=True, exist_ok=True)

    @property
    def directory(self) -> Path:
        return self._directory

    def default_path(self) -> Path:
        return self._directory / "default_context.json"

    def load(self, path: Path | None = None) -> ApplicationContextDTO:
        target = path or self.default_path()
        if not target.exists():
            return ApplicationContextDTO()

        payload = _read_json(target)
        if payload is None:
            return ApplicationContextDTO()

        return _context_from_payload(payload)

    def save(
        self,
        context: ApplicationContextDTO,
        path: Path | None = None,
    ) -> Path:
        target = self._normalize_path(path or self.default_path())
        return _write_json(target, _context_to_payload(context))

    def _normalize_path(self, path: Path) -> Path:
        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")
        if not path.is_absolute() or self._directory not in path.parents:
            path = self._directory / path.name
        return path


class WorkspaceStateRepository:

    def __init__(self, root: Path):
        self._directory = root / "data" / "workspaces"
        self._directory.mkdir(parents=True, exist_ok=True)

    @property
    def directory(self) -> Path:
        return self._directory

    def load(self, path: Path) -> WorkspaceStateDTO:
        target = self._normalize_path(path)
        if not target.exists():
            return WorkspaceStateDTO()

        payload = _read_json(target)
        if payload is None:
            return WorkspaceStateDTO()

        context_payload = payload.get("context", payload)
        return WorkspaceStateDTO(context=_context_from_payload(context_payload))

    def save(
        self,
        workspace: WorkspaceStateDTO,
        path: Path | None = None,
    ) -> Path:
        target = self._normalize_path(path or (self._directory / "workspace.json"))
        return _write_json(target, _context_to_payload(workspace.context))

    def _normalize_path(self, path: Path) -> Path:
        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")
        if not path.is_absolute() or self._directory not in path.parents:
            path = self._directory / path.name
        return path
