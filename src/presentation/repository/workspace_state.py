from pathlib import Path

from src.application.dto.application_state import (
    ApplicationContextDTO,
    WorkspaceStateDTO,
)
from src.presentation.repository.context_payload import (
    context_from_payload,
    context_to_payload,
    normalize_json_path,
    read_json,
    write_json,
)


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

        payload = read_json(target)
        if payload is None:
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

        payload = read_json(target)
        if payload is None:
            return WorkspaceStateDTO()

        context_payload = payload.get("context", payload)
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
