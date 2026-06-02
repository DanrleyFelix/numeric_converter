from pathlib import Path

from src.modules.binary_workbench_use_cases import (
    BinaryWorkbenchPreferencesUseCase,
    BinaryWorkbenchProgramContextUseCase,
    binary_version_has_unsaved_edits,
    rows_have_meaningful_edits,
)
from src.modules.dtos import (
    BinaryWorkbenchPreferencesDTO,
    BinaryWorkbenchRowDTO,
    BinaryWorkbenchTabContextDTO,
    ProgramContextDTO,
)


class BinaryWorkbenchController:
    def __init__(
        self,
        program_context_use_case: BinaryWorkbenchProgramContextUseCase | None = None,
        preferences_use_case: BinaryWorkbenchPreferencesUseCase | None = None,
    ) -> None:
        self._program_context_use_case = (
            program_context_use_case or BinaryWorkbenchProgramContextUseCase()
        )
        self._preferences_use_case = preferences_use_case or BinaryWorkbenchPreferencesUseCase()

    def remember_recent_file(
        self,
        context: ProgramContextDTO,
        path: Path,
    ) -> ProgramContextDTO:
        return self._program_context_use_case.remember_recent_file(context, path)

    def remember_workspace(
        self,
        context: ProgramContextDTO,
        source_path: Path,
        workspace_path: Path,
    ) -> ProgramContextDTO:
        return self._program_context_use_case.remember_workspace(
            context,
            source_path,
            workspace_path,
        )

    def preferred_workspace(
        self,
        context: ProgramContextDTO,
        source_path: Path,
    ) -> Path | None:
        return self._program_context_use_case.preferred_workspace(context, source_path)

    def normalize_preferences(
        self,
        preferences: BinaryWorkbenchPreferencesDTO,
    ) -> BinaryWorkbenchPreferencesDTO:
        return self._preferences_use_case.normalize(preferences)

    def version_has_unsaved_edits(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> bool:
        return binary_version_has_unsaved_edits(context)

    def rows_have_unsaved_edits(
        self,
        rows: list[BinaryWorkbenchRowDTO],
        original_rows: list[BinaryWorkbenchRowDTO],
    ) -> bool:
        return rows_have_meaningful_edits(rows, original_rows)
