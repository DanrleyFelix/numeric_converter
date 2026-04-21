from pathlib import Path

from src.application.contracts.state_contract import (
    IApplicationContextRepository,
    IWorkspaceStateRepository,
)
from src.application.dto.application_state import (
    ApplicationContextDTO,
    WorkspaceStateDTO,
)


class WorkspaceStateService:

    def __init__(
        self,
        context_repository: IApplicationContextRepository,
        workspace_repository: IWorkspaceStateRepository,
    ):
        self._context_repository = context_repository
        self._workspace_repository = workspace_repository

    @property
    def context_directory(self) -> Path:
        return self._context_repository.directory

    @property
    def workspace_directory(self) -> Path:
        return self._workspace_repository.directory

    def load_default_context(self) -> ApplicationContextDTO:
        return self._context_repository.load()

    def save_default_context(self, context: ApplicationContextDTO) -> Path:
        return self._context_repository.save(context)

    def load_context(self, path: Path) -> ApplicationContextDTO:
        return self._context_repository.load(path)

    def save_context(self, context: ApplicationContextDTO, path: Path) -> Path:
        return self._context_repository.save(context, path)

    def load_workspace(self, path: Path) -> WorkspaceStateDTO:
        return self._workspace_repository.load(path)

    def save_workspace(
        self,
        context: ApplicationContextDTO,
        path: Path,
    ) -> Path:
        return self._workspace_repository.save(
            WorkspaceStateDTO(context=context),
            path,
        )
