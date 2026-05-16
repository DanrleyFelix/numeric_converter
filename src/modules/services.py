from pathlib import Path

from src.modules.dtos import (
    ApplicationContextDTO,
    BinaryWorkbenchPreferencesDTO,
    BinaryWorkbenchStateDTO,
    FormattingOutputDTO,
    NumericWorkbenchPreferencesDTO,
    ProgramContextDTO,
    WorkspaceStateDTO,
)


class FormattingPreferencesService:
    def __init__(self, repository) -> None:
        self._repository = repository

    def get_format(self) -> dict[str, FormattingOutputDTO]:
        return self._repository.load()

    def get_preferences(self) -> NumericWorkbenchPreferencesDTO:
        return self._repository.load_preferences()

    def update(self, key: str, context: FormattingOutputDTO) -> None:
        current = self._repository.load()
        current[key] = context
        self._repository.save(current)

    def update_numeric_flags(
        self,
        key_panel_visible: bool,
        auto_convert_enabled: bool,
    ) -> None:
        preferences = self._repository.load_preferences()
        self._repository.save_preferences(
            NumericWorkbenchPreferencesDTO(
                formatters=preferences.formatters,
                key_panel_visible=key_panel_visible,
                auto_convert_enabled=auto_convert_enabled,
            )
        )


class BinaryWorkbenchPreferencesService:
    def __init__(self, repository) -> None:
        self._repository = repository

    def load(self) -> BinaryWorkbenchPreferencesDTO:
        return self._repository.load()

    def save(self, preferences: BinaryWorkbenchPreferencesDTO) -> None:
        self._repository.save(preferences)


class WorkspaceStateService:
    def __init__(
        self,
        context_repository,
        workspace_repository,
        binary_context_repository,
        program_context_repository,
    ) -> None:
        self._context_repository = context_repository
        self._workspace_repository = workspace_repository
        self._binary_context_repository = binary_context_repository
        self._program_context_repository = program_context_repository

    @property
    def context_directory(self) -> Path:
        return self._context_repository.directory

    @property
    def workspace_directory(self) -> Path:
        return self._workspace_repository.directory

    @property
    def binary_workspace_directory(self) -> Path:
        return self._workspace_repository.binary_directory

    @property
    def program_context_path(self) -> Path:
        return self._program_context_repository.file

    @property
    def default_context_path(self) -> Path:
        return self._context_repository.default_path()

    def load_default_context(self) -> ApplicationContextDTO:
        return self._context_repository.load()

    def save_default_context(self, context: ApplicationContextDTO) -> Path:
        return self._context_repository.save(context)

    def load_default_binary_context(self) -> BinaryWorkbenchStateDTO:
        return self._binary_context_repository.load()

    def save_default_binary_context(self, state: BinaryWorkbenchStateDTO) -> Path:
        return self._binary_context_repository.save(state)

    def load_program_context(self) -> ProgramContextDTO:
        return self._program_context_repository.load()

    def save_program_context(self, context: ProgramContextDTO) -> Path:
        return self._program_context_repository.save(context)

    def load_context(self, path: Path) -> ApplicationContextDTO:
        return self._context_repository.load(path)

    def save_context(self, context: ApplicationContextDTO, path: Path) -> Path:
        return self._context_repository.save(context, path)

    def load_workspace(self, path: Path) -> WorkspaceStateDTO:
        return self._workspace_repository.load(path)

    def save_workspace(self, context: ApplicationContextDTO, path: Path) -> Path:
        return self._workspace_repository.save(WorkspaceStateDTO(context=context), path)
