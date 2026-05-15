from __future__ import annotations

from pathlib import Path

from src.modules.dtos import (
    BinaryWorkbenchMemoryRegionDTO,
    BinaryWorkbenchTabContextDTO,
)
from src.core.binary_workbench.file_ops import overlay_from_version_rows
from src.presentation.repository.binary_workbench_workspace.constants import (
    LBA_FILESYSTEM,
    MEMORY_REGIONS,
    SYMBOLS,
    VERSIONS,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_STATE,
)
from src.presentation.ui.components.binary_workbench.symbols import symbol_offsets

DIRECTORY_KEYS = {
    BINARY_WORKBENCH_STATE.SYMBOLS_DIRECTORY: SYMBOLS,
    BINARY_WORKBENCH_STATE.LBA_FILESYSTEM_DIRECTORY: LBA_FILESYSTEM,
    BINARY_WORKBENCH_STATE.MEMORY_REGIONS_DIRECTORY: MEMORY_REGIONS,
    BINARY_WORKBENCH_STATE.VERSIONS_DIRECTORY: VERSIONS,
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
        if self._has_unsaved_version_edits(current) and current.active_version_name:
            self.update_current_version(current.active_version_name)
            current = self.current_context()
            if current is None:
                return False
        updated = self._workspace_repository.save_tab_workspace(current, path)
        self._set_current_context(self._with_symbol_offsets(updated))
        return True

    def set_current_memory_regions(
        self,
        regions: list[BinaryWorkbenchMemoryRegionDTO],
    ) -> None:
        current = self.current_context()
        if current is None:
            return
        self._set_current_context(
            BinaryWorkbenchTabContextDTO(**{**current.__dict__, "memory_regions": regions})
        )

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
        manifest = self._workspace_repository.find_for_source(path)
        if manifest is None:
            return context
        return self._with_symbol_offsets(
            self._workspace_repository.load_tab_workspace(context, manifest)
        )

    def _has_workspace_module_changes(self, context: BinaryWorkbenchTabContextDTO) -> bool:
        current = self._workspace_repository.checksums_for_tab(context)
        if context.module_checksums:
            return any(current.get(key) != value for key, value in context.module_checksums.items())
        return any(
            (
                context.variables,
                context.equates,
                context.internal_files,
                context.memory_regions,
                context.versions,
            )
        )

    def _has_unsaved_version_edits(self, context: BinaryWorkbenchTabContextDTO) -> bool:
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

    def _with_symbol_offsets(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> BinaryWorkbenchTabContextDTO:
        return BinaryWorkbenchTabContextDTO(
            **{
                **context.__dict__,
                "symbol_offsets": symbol_offsets(
                    context.rows,
                    context.variables,
                    context.equates,
                    context.labels,
                ),
            }
        )
