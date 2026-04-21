import json
from pathlib import Path
from typing import Any

from src.application.dto.application_state import (
    ApplicationContextDTO,
    CommandContextDTO,
    CommandLogDTO,
    ConverterStateDTO,
)
from src.application.dto.command_entry import CommandEntryDTO, CommandLogEntryDTO


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

        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return ApplicationContextDTO()

        converter_raw = payload.get("converter", {})
        command_raw = payload.get("command", {})

        return ApplicationContextDTO(
            converter=ConverterStateDTO(
                from_type=converter_raw.get("from_type", "decimal"),
                fields=self._converter_fields(converter_raw.get("fields", {})),
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
            ),
            key_panel_visible=payload.get("key_panel_visible", True),
        )

    def save(
        self,
        context: ApplicationContextDTO,
        path: Path | None = None,
    ) -> Path:
        target = self._normalize_path(path or self.default_path())
        payload = {
            "converter": {
                "from_type": context.converter.from_type,
                "fields": self._converter_fields(context.converter.fields),
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
            },
            "key_panel_visible": context.key_panel_visible,
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(payload, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
        return target

    def _normalize_path(self, path: Path) -> Path:
        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")
        if not path.is_absolute() or self._directory not in path.parents:
            path = self._directory / path.name
        return path

    def _converter_fields(self, raw: dict[str, Any]) -> dict[str, str]:
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


class CommandLogRepository:

    def __init__(self, root: Path):
        self._directory = root / "data" / "logs"
        self._directory.mkdir(parents=True, exist_ok=True)

    @property
    def directory(self) -> Path:
        return self._directory

    def default_path(self) -> Path:
        return self._directory / "default_log.json"

    def load(self, path: Path | None = None) -> CommandLogDTO:
        target = path or self.default_path()
        if not target.exists():
            return CommandLogDTO()

        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return CommandLogDTO()

        return CommandLogDTO(
            entries=[
                CommandLogEntryDTO(
                    input=item.get("input", ""),
                    success=bool(item.get("success", False)),
                    message=item.get("message"),
                    result=item.get("result"),
                )
                for item in payload.get("entries", [])
            ]
        )

    def save(self, log: CommandLogDTO, path: Path | None = None) -> Path:
        target = self._normalize_path(path or self.default_path())
        payload = {
            "entries": [
                {
                    "input": entry.input,
                    "success": entry.success,
                    "message": entry.message,
                    "result": entry.result,
                }
                for entry in log.entries
            ]
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(payload, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
        return target

    def _normalize_path(self, path: Path) -> Path:
        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")
        if not path.is_absolute() or self._directory not in path.parents:
            path = self._directory / path.name
        return path
