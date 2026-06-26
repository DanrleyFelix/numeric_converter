import json
import re
from pathlib import Path

from src.modules.application_dtos import (
    ApplicationContextDTO,
    ProgramContextDTO,
    WorkspaceStateDTO,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchStateDTO
from src.presentation.repository.binary_workbench_payload import (
    binary_workbench_state_from_payload,
    binary_workbench_state_to_payload,
)
from src.presentation.repository.context_payload import (
    context_from_payload,
    context_to_payload
)

from src.modules.utils import normalize_json_path, read_json, write_json

SEARCH_CACHE_PAYLOAD_PATTERN = re.compile(
    r'("search_cache"\s*:\s*)\{.*?\}',
    re.DOTALL,
)


class ApplicationContextRepository:

    def __init__(self, root: Path):
        self._legacy_path = root / "data" / "contexts" / "default_context.json"
        self._directory = root / "data" / "numeric_workbench" / "contexts"
        self._directory.mkdir(parents=True, exist_ok=True)

    @property
    def directory(self) -> Path:
        return self._directory

    def default_path(self) -> Path:
        return self._directory / "default.json"

    def load(self, path: Path | None = None) -> ApplicationContextDTO:
        target = path or self.default_path()
        if path is None and not target.exists() and self._legacy_path.exists():
            target = self._legacy_path
        if not target.exists():
            return ApplicationContextDTO()

        payload = read_json(target)
        if not isinstance(payload, dict):
            return ApplicationContextDTO()

        return context_from_payload(payload)

    def save(
        self,
        context: ApplicationContextDTO,
        path: Path | None = None,
    ) -> Path:
        target = self._normalize_path(path or self.default_path())
        return write_json(target, context_to_payload(context))

    def _normalize_path(self, path: Path) -> Path:
        return normalize_json_path(path, self._directory)


class BinaryWorkbenchContextRepository:

    def __init__(self, root: Path):
        self._legacy_path = root / "data" / "contexts" / "default_context.json"
        self._directory = root / "data" / "binary_workbench" / "contexts"
        self._directory.mkdir(parents=True, exist_ok=True)

    @property
    def directory(self) -> Path:
        return self._directory

    def default_path(self) -> Path:
        return self._directory / "default.json"

    def load(self, path: Path | None = None) -> BinaryWorkbenchStateDTO:
        target = path or self.default_path()
        if path is None and not target.exists() and self._legacy_path.exists():
            payload = _read_binary_workbench_json(self._legacy_path)
            if isinstance(payload, dict):
                binary_payload = payload.get("binary_workbench", {})
                binary_payload = dict(binary_payload) if isinstance(binary_payload, dict) else {}
                window_sizes = payload.get("window_sizes", {})
                if isinstance(window_sizes, dict):
                    binary_payload["window_size"] = window_sizes.get("binary_workbench_window")
                return binary_workbench_state_from_payload(binary_payload)
            return BinaryWorkbenchStateDTO()
        if not target.exists():
            return BinaryWorkbenchStateDTO()
        payload = _read_binary_workbench_json(target)
        if not isinstance(payload, dict):
            return BinaryWorkbenchStateDTO()
        return binary_workbench_state_from_payload(payload)

    def save(
        self,
        state: BinaryWorkbenchStateDTO,
        path: Path | None = None,
    ) -> Path:
        target = self._normalize_path(path or self.default_path())
        return write_json(target, binary_workbench_state_to_payload(state))

    def _normalize_path(self, path: Path) -> Path:
        return normalize_json_path(path, self._directory)


def _read_binary_workbench_json(path: Path) -> object:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    if '"search_cache"' in text:
        text = SEARCH_CACHE_PAYLOAD_PATTERN.sub(r"\1{}", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


class ProgramContextRepository:

    def __init__(self, root: Path):
        self._file = root / "data" / "program_context.json"
        self._legacy_path = root / "data" / "contexts" / "default_context.json"
        self._file.parent.mkdir(parents=True, exist_ok=True)

    @property
    def file(self) -> Path:
        return self._file

    def load(self) -> ProgramContextDTO:
        payload = read_json(self._file)
        if isinstance(payload, dict):
            return self._from_payload(payload)
        legacy = read_json(self._legacy_path)
        if not isinstance(legacy, dict):
            return ProgramContextDTO()
        binary = legacy.get("binary_workbench", {})
        binary = binary if isinstance(binary, dict) else {}
        return ProgramContextDTO(
            recent_files=[
                str(item)
                for item in binary.get("recent_files", [])
                if isinstance(item, str)
            ],
            last_binary_workspaces={},
        )

    def save(self, context: ProgramContextDTO) -> Path:
        return write_json(
            self._file,
            {
                "recent_files": list(context.recent_files),
                "last_binary_workspaces": dict(context.last_binary_workspaces),
            },
        )

    def _from_payload(self, payload: dict[str, object]) -> ProgramContextDTO:
        recent = payload.get("recent_files")
        workspaces = payload.get("last_binary_workspaces")
        return ProgramContextDTO(
            recent_files=[str(item) for item in recent if isinstance(item, str)]
            if isinstance(recent, list)
            else [],
            last_binary_workspaces={
                str(key): str(value)
                for key, value in workspaces.items()
                if isinstance(value, str)
            }
            if isinstance(workspaces, dict)
            else {},
        )


class WorkspaceStateRepository:

    def __init__(self, root: Path):
        self._directory = root / "data" / "numeric_workbench" / "workspaces"
        self._binary_directory = root / "data" / "binary_workbench" / "workspaces"
        self._directory.mkdir(parents=True, exist_ok=True)
        self._binary_directory.mkdir(parents=True, exist_ok=True)

    @property
    def directory(self) -> Path:
        return self._directory

    @property
    def binary_directory(self) -> Path:
        return self._binary_directory

    def load(self, path: Path) -> WorkspaceStateDTO:
        target = self._normalize_path(path)
        if not target.exists():
            return WorkspaceStateDTO()

        payload = read_json(target)
        if not isinstance(payload, dict):
            return WorkspaceStateDTO()

        context_payload = payload.get("context", payload)
        if not isinstance(context_payload, dict):
            return WorkspaceStateDTO()
        return WorkspaceStateDTO(context=context_from_payload(context_payload))

    def save(
        self,
        workspace: WorkspaceStateDTO,
        path: Path | None = None,
    ) -> Path:
        target = self._normalize_path(path or (self._directory / "workspace.json"))
        return write_json(target, context_to_payload(workspace.context))

    def _normalize_path(self, path: Path) -> Path:
        return normalize_json_path(path, self._directory)
