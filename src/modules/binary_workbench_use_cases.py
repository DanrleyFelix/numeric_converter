from pathlib import Path

from src.core.binary_workbench.file_ops import overlay_from_version_rows
from src.core.binary_workbench.resource_identity import file_resource_identifiers
from src.modules.dtos import (
    BinaryWorkbenchPreferencesDTO,
    BinaryWorkbenchTabContextDTO,
    ProgramContextDTO,
)


class BinaryWorkbenchProgramContextUseCase:
    def __init__(self, recent_limit: int = 20) -> None:
        self._recent_limit = recent_limit

    def remember_recent_file(
        self,
        context: ProgramContextDTO,
        path: Path,
    ) -> ProgramContextDTO:
        text_path = str(path)
        recent = [
            text_path,
            *[item for item in context.recent_files if item != text_path],
        ][: self._recent_limit]
        return ProgramContextDTO(
            recent_files=recent,
            last_binary_workspaces=dict(context.last_binary_workspaces),
        )

    def remember_workspace(
        self,
        context: ProgramContextDTO,
        source_path: Path,
        workspace_path: Path,
    ) -> ProgramContextDTO:
        return ProgramContextDTO(
            recent_files=list(context.recent_files),
            last_binary_workspaces={
                **context.last_binary_workspaces,
                self._source_key(source_path): str(workspace_path),
            },
        )

    def preferred_workspace(
        self,
        context: ProgramContextDTO,
        source_path: Path,
    ) -> Path | None:
        value = context.last_binary_workspaces.get(self._source_key(source_path))
        return Path(value) if value else None

    def _source_key(self, path: Path) -> str:
        identifiers = file_resource_identifiers(path)
        return identifiers[0] if identifiers else f"path:{str(path).lower()}"


class BinaryWorkbenchPreferencesUseCase:
    def normalize(
        self,
        preferences: BinaryWorkbenchPreferencesDTO,
    ) -> BinaryWorkbenchPreferencesDTO:
        return BinaryWorkbenchPreferencesDTO(
            group_bytes=preferences.group_bytes if preferences.group_bytes in {1, 2, 4} else 1,
            uppercase_bytes=preferences.uppercase_bytes,
            uppercase_instructions=preferences.uppercase_instructions,
            block_size=max(1, preferences.block_size),
            cache_max_blocks=max(1, preferences.cache_max_blocks),
        )


def binary_version_has_unsaved_edits(
    context: BinaryWorkbenchTabContextDTO,
) -> bool:
    if context.version_dirty:
        return True
    if not context.byte_overlays and not context.instruction_overlays:
        return False
    if not context.active_version_name:
        return True
    version = next(
        (item for item in context.versions if item.name == context.active_version_name),
        None,
    )
    if version is None:
        return True
    saved_bytes = overlay_from_version_rows(version.rows)
    return (
        dict(context.instruction_overlays) != dict(version.instruction_overlays)
        or dict(context.byte_overlays) != saved_bytes
    )
