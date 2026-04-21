from pathlib import Path

from src.application.contracts.state_contract import (
    IApplicationContextRepository,
    ICommandLogRepository,
    IWorkspaceStateRepository,
)
from src.application.dto.application_state import (
    ApplicationContextDTO,
    CommandLogDTO,
    WorkspaceStateDTO,
)


class WorkspaceStateService:

    def __init__(
        self,
        context_repository: IApplicationContextRepository,
        log_repository: ICommandLogRepository,
        workspace_repository: IWorkspaceStateRepository,
    ):
        self._context_repository = context_repository
        self._log_repository = log_repository
        self._workspace_repository = workspace_repository

    @property
    def context_directory(self) -> Path:
        return self._context_repository.directory

    @property
    def log_directory(self) -> Path:
        return self._log_repository.directory

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

    def load_default_log(self) -> CommandLogDTO:
        return self._log_repository.load()

    def save_default_log(self, log: CommandLogDTO) -> Path:
        return self._log_repository.save(log)

    def load_log(self, path: Path) -> CommandLogDTO:
        return self._log_repository.load(path)

    def save_log(self, log: CommandLogDTO, path: Path) -> Path:
        return self._log_repository.save(log, path)

    def load_workspace(self, path: Path) -> WorkspaceStateDTO:
        return self._workspace_repository.load(path)

    def save_workspace(
        self,
        context: ApplicationContextDTO,
        log: CommandLogDTO,
        path: Path,
    ) -> Path:
        return self._workspace_repository.save(
            WorkspaceStateDTO(context=context, log=log),
            path,
        )
