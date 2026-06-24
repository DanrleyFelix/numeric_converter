from pathlib import Path

from src.core.binary_workbench.file_ops import overlay_from_version_rows
from src.core.binary_workbench.codec_registry import binary_workbench_codec_for
from src.core.binary_workbench.selection_limits import normalized_selection_limit
from src.core.binary_workbench.version_overlays import without_blank_instruction_overlays
from src.core.binary_workbench.version_instruction_maps import version_instruction_maps
from src.core.binary_workbench.resource_identity import file_resource_identifiers
from src.modules.application_dtos import ProgramContextDTO
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_BYTE_GROUP_OPTIONS
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchPreferencesDTO,
    BinaryWorkbenchRowDTO,
    BinaryWorkbenchTabContextDTO,
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
            group_bytes=(
                preferences.group_bytes
                if preferences.group_bytes in BINARY_WORKBENCH_BYTE_GROUP_OPTIONS
                else BINARY_WORKBENCH_BYTE_GROUP_OPTIONS[0]
            ),
            uppercase_bytes=preferences.uppercase_bytes,
            uppercase_instructions=preferences.uppercase_instructions,
            block_size=max(1, preferences.block_size),
            cache_max_blocks=max(1, preferences.cache_max_blocks),
            selection_limit_bytes=normalized_selection_limit(preferences.selection_limit_bytes),
            binary_edit_rules=preferences.binary_edit_rules,
            assembly_edit_rules=preferences.assembly_edit_rules,
        )


def binary_version_has_unsaved_edits(
    context: BinaryWorkbenchTabContextDTO,
) -> bool:
    byte_overlays, instruction_overlays = _meaningful_overlays(
        context.byte_overlays,
        context.instruction_overlays,
    )
    if not context.active_version_name:
        return bool(byte_overlays or instruction_overlays)
    version = next(
        (item for item in context.versions if item.name == context.active_version_name),
        None,
    )
    if version is None:
        return bool(byte_overlays or instruction_overlays)
    saved_bytes, saved_instructions = _meaningful_overlays(
        overlay_from_version_rows(version.rows),
        version.instruction_overlays,
    )
    current_instructions, current_lines = version_instruction_maps(
        context.rows,
        context.instruction_overlays,
        binary_workbench_codec_for(context.cpu_arch),
        context.labels,
        context.variables,
        context.equates,
    )
    return (
        current_instructions != saved_instructions
        or current_lines != version.instructions_by_line
        or byte_overlays != saved_bytes
    )


def rows_have_meaningful_edits(
    rows: list[BinaryWorkbenchRowDTO],
    original_rows: list[BinaryWorkbenchRowDTO],
) -> bool:
    return _meaningful_rows(rows) != _meaningful_rows(original_rows)


def _meaningful_map(values: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in values.items() if value.strip()}


def _meaningful_overlays(
    byte_overlays: dict[str, str],
    instruction_overlays: dict[str, str],
) -> tuple[dict[str, str], dict[str, str]]:
    byte_overlays, instruction_overlays = without_blank_instruction_overlays(
        dict(byte_overlays),
        dict(instruction_overlays),
    )
    return _meaningful_map(byte_overlays), _meaningful_map(instruction_overlays)


def _meaningful_rows(rows: list[BinaryWorkbenchRowDTO]) -> list[tuple[str, str]]:
    return [
        normalized
        for row in rows
        if any(
            normalized := (
                _without_whitespace(row.instruction),
                _without_whitespace(row.bytes_text),
            )
        )
    ]


def _without_whitespace(value: str) -> str:
    return "".join(value.split())
