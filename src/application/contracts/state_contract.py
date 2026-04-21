from pathlib import Path
from typing import Protocol

from src.application.dto.application_state import (
    ApplicationContextDTO,
    CommandLogDTO,
    WorkspaceStateDTO,
)


class IApplicationContextRepository(Protocol):

    @property
    def directory(self) -> Path:
        pass

    def default_path(self) -> Path:
        pass

    def load(self, path: Path | None = None) -> ApplicationContextDTO:
        pass

    def save(self, context: ApplicationContextDTO, path: Path | None = None) -> Path:
        pass


class ICommandLogRepository(Protocol):

    @property
    def directory(self) -> Path:
        pass

    def default_path(self) -> Path:
        pass

    def load(self, path: Path | None = None) -> CommandLogDTO:
        pass

    def save(self, log: CommandLogDTO, path: Path | None = None) -> Path:
        pass


class IWorkspaceStateRepository(Protocol):

    @property
    def directory(self) -> Path:
        pass

    def load(self, path: Path) -> WorkspaceStateDTO:
        pass

    def save(self, workspace: WorkspaceStateDTO, path: Path | None = None) -> Path:
        pass
