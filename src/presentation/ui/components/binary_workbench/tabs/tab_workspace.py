from __future__ import annotations

from pathlib import Path

from src.modules.dtos import (
    BinaryWorkbenchMemoryRegionDTO,
    BinaryWorkbenchTabContextDTO,
)
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
        if self.has_unsaved_version_edits(current) and current.active_version_name:
            self.update_current_version(current.active_version_name)
            current = self.current_context()
            if current is None:
                return False
        updated = self._workspace_repository.save_tab_workspace(current, path)
        self._remember_workspace_for_source(updated)
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
                context.memory_regions,
                context.versions,
            )
        )

    def has_unsaved_version_edits(self, context: BinaryWorkbenchTabContextDTO) -> bool:
        return self._controller.version_has_unsaved_edits(context)

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
