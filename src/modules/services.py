from pathlib import Path

from src.modules.dtos import ApplicationContextDTO, FormattingOutputDTO, WorkspaceStateDTO


class FormattingPreferencesService:
    def __init__(self, repository) -> None:
        self._repository = repository

    def get_format(self) -> dict[str, FormattingOutputDTO]:
        return self._repository.load()

    def update(self, key: str, context: FormattingOutputDTO) -> None:
        current = self._repository.load()
        current[key] = context
        self._repository.save(current)


class WorkspaceStateService:
    def __init__(self, context_repository, workspace_repository) -> None:
        self._context_repository = context_repository
        self._workspace_repository = workspace_repository

    @property
    def context_directory(self) -> Path:
        return self._context_repository.directory

    @property
    def workspace_directory(self) -> Path:
        return self._workspace_repository.directory

    @property
    def default_context_path(self) -> Path:
        return self._context_repository.default_path()

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

    def save_workspace(self, context: ApplicationContextDTO, path: Path) -> Path:
        return self._workspace_repository.save(WorkspaceStateDTO(context=context), path)
