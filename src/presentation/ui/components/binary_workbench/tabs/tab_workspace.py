from __future__ import annotations

from pathlib import Path

from src.core.binary_workbench.codec_registry import binary_workbench_codec_for
from src.core.binary_workbench.mips_r3000a import build_source_line_rows
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_STATE,
    BINARY_WORKBENCH_TAB_KIND,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO, BinaryWorkbenchViewPreferencesDTO
from src.presentation.repository.binary_workbench_workspace.constants import (
    COMMANDS,
    LBA_FILESYSTEM,
    OFFSET_REGIONS,
    SYMBOLS,
    VERSIONS,
)
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    labels_from_rows,
)
from src.presentation.ui.components.binary_workbench.symbols import symbol_offsets

DIRECTORY_KEYS = {
    BINARY_WORKBENCH_STATE.SYMBOLS_DIRECTORY: SYMBOLS,
    BINARY_WORKBENCH_STATE.LBA_FILESYSTEM_DIRECTORY: LBA_FILESYSTEM,
    BINARY_WORKBENCH_STATE.OFFSET_REGIONS_DIRECTORY: OFFSET_REGIONS,
    BINARY_WORKBENCH_STATE.VERSIONS_DIRECTORY: VERSIONS,
    BINARY_WORKBENCH_STATE.COMMANDS_DIRECTORY: COMMANDS,
}


class TabWorkspaceMixin:
    def workspace_module_directory(self, action_key: str) -> str:
        current = self.current_context()
        module_key = DIRECTORY_KEYS.get(action_key)
        if current is not None and module_key:
            if value := current.module_directories.get(module_key):
                return value
        defaults = self._workspace_repository.default_module_directories()
        return defaults.get(module_key or "", "")

    def save_current_workspace(self, path: Path | None = None) -> bool:
        current = self.current_context()
        if current is None:
            return False
        if self.has_unsaved_version_edits(current) and current.active_version_name:
            self.update_current_version(current.active_version_name)
            current = self.current_context()
            if current is None:
                return False
        updated = self._workspace_repository.save_tab_workspace(current, path)
        self._remember_workspace_for_source(updated)
        self._set_current_context(self._with_symbol_offsets(updated))
        return True

    def set_current_module_path(self, module_key: str, path: Path) -> None:
        current = self.current_context()
        if current is None:
            return
        self._set_current_context(
            BinaryWorkbenchTabContextDTO(
                **{
                    **current.__dict__,
                    "module_paths": {**current.module_paths, module_key: str(path)},
                    "module_directories": {
                        **current.module_directories,
                        module_key: str(path.parent),
                    },
                }
            )
        )

    def _apply_matching_workspace(
        self,
        context: BinaryWorkbenchTabContextDTO,
        path: Path,
    ) -> BinaryWorkbenchTabContextDTO:
        manifest = self._workspace_repository.find_for_source(
            path,
            self._controller.preferred_workspace(
                self._program_context,
                path,
            ),
        )
        if manifest is None:
            return context
        updated = self._with_symbol_offsets(
            self._workspace_repository.load_tab_workspace(context, manifest)
        )
        self._remember_workspace_for_source(updated)
        return updated

    def _remember_workspace_for_source(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> None:
        if not context.source_path or not context.workspace_path:
            return
        self._program_context = self._controller.remember_workspace(
            self._program_context,
            Path(context.source_path),
            Path(context.workspace_path),
        )
        self.programContextChanged.emit(self._program_context)

    def _has_workspace_module_changes(self, context: BinaryWorkbenchTabContextDTO) -> bool:
        current = self._workspace_repository.checksums_for_tab(context)
        if context.module_checksums:
            return any(current.get(key) != value for key, value in context.module_checksums.items())
        return any(
            (
                context.variables,
                context.equates,
                context.internal_files,
                context.versions,
                context.custom_commands,
                context.encoding_tables,
                context.offset_regions,
                context.view_preferences != BinaryWorkbenchViewPreferencesDTO(),
            )
        )

    def has_unsaved_version_edits(self, context: BinaryWorkbenchTabContextDTO) -> bool:
        return self._controller.version_has_unsaved_edits(context)

    def _with_symbol_offsets(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> BinaryWorkbenchTabContextDTO:
        rows = _rows_with_loaded_symbols(context)
        labels = labels_from_rows(rows) if rows is not context.rows else context.labels
        return BinaryWorkbenchTabContextDTO(
            **{
                **context.__dict__,
                "rows": rows,
                "labels": labels,
                "symbol_offsets": symbol_offsets(
                    rows,
                    context.variables,
                    context.equates,
                    labels,
                ),
            }
        )


def _rows_with_loaded_symbols(
    context: BinaryWorkbenchTabContextDTO,
):
    if context.kind not in {BINARY_WORKBENCH_TAB_KIND.ASSEMBLY, BINARY_WORKBENCH_TAB_KIND.SCRATCH}:
        return context.rows
    if not (context.variables or context.equates):
        return context.rows
    rows = build_source_line_rows(
        [row.instruction for row in context.rows],
        list(context.reference_offsets),
        dict(context.reference_offset_bases),
        binary_workbench_codec_for(context.cpu_arch),
        _first_file_offset(context.rows),
        variables=context.variables,
        equates=context.equates,
    )
    return rows or context.rows


def _first_file_offset(rows) -> int:
    for row in rows:
        value = row.offsets.get("File")
        if not value or value == "-":
            continue
        try:
            return int(value, 0)
        except ValueError:
            return 0
    return 0
