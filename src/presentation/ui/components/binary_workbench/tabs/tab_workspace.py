from __future__ import annotations

from pathlib import Path

from src.core.binary_workbench.codec_registry import binary_workbench_codec_for
from src.core.binary_workbench.internal_file_patch import (
    binary_overlays_from_internal_overlays,
)
from src.core.binary_workbench.internal_file_region import define_internal_file_region
from src.core.binary_workbench.internal_offset_mapper import InternalOffsetMapper
from src.core.binary_workbench.mips_r3000a import build_source_line_rows
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_DEFAULT_VERSION_NAME,
    BINARY_WORKBENCH_STATE,
    BINARY_WORKBENCH_TAB_KIND,
)
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchViewPreferencesDTO,
)
from src.presentation.repository.binary_workbench_workspace.constants import (
    LBA_FILESYSTEM,
    OFFSET_REGIONS,
    SYMBOLS,
    VERSIONS,
)
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    merged_instruction_labels,
    rows_from_overlays,
)
from src.presentation.ui.components.binary_workbench.symbols import symbol_offsets
from src.presentation.ui.components.binary_workbench.tabs.workspace_memory import (
    workspace_heavy_context_unloaded,
)

DIRECTORY_KEYS = {
    BINARY_WORKBENCH_STATE.SYMBOLS_DIRECTORY: SYMBOLS,
    BINARY_WORKBENCH_STATE.LBA_FILESYSTEM_DIRECTORY: LBA_FILESYSTEM,
    BINARY_WORKBENCH_STATE.OFFSET_REGIONS_DIRECTORY: OFFSET_REGIONS,
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
        if current.kind == BINARY_WORKBENCH_TAB_KIND.INTERNAL:
            return self._save_internal_parent_workspace(current, path)
        if self.has_unsaved_version_edits(current) and current.active_version_name:
            self.update_current_version(current.active_version_name)
            current = self.current_context()
            if current is None:
                return False
        updated = self._workspace_repository.save_tab_workspace(current, path)
        self._remember_workspace_for_source(updated)
        self._set_current_context(self._with_symbol_offsets(updated))
        return True

    def _save_internal_parent_workspace(
        self,
        current: BinaryWorkbenchTabContextDTO,
        path: Path | None,
    ) -> bool:
        parent = self._internal_parent_context(current)
        mapper = _internal_workspace_mapper(current)
        if parent is None or mapper is None:
            return False

        parent_mapped = binary_overlays_from_internal_overlays(
            mapper,
            current.byte_overlays,
        )
        controlled_offsets = {*parent_mapped, *current.internal_parent_byte_overlays}
        parent_overlays = dict(parent.byte_overlays)
        for offset in controlled_offsets:
            parent_overlays.pop(offset, None)
        parent_overlays.update(parent_mapped)
        parent = BinaryWorkbenchTabContextDTO(
            **{
                **parent.__dict__,
                "byte_overlays": parent_overlays,
                "version_dirty": parent.version_dirty or parent_overlays != parent.byte_overlays,
            }
        )

        internal_version_name = (
            current.active_version_name or BINARY_WORKBENCH_DEFAULT_VERSION_NAME
        )
        internal_version = self._version_from_current(internal_version_name, current)
        internal_versions = [
            version
            for version in current.versions
            if version.name != internal_version_name
        ]
        updated_internal = BinaryWorkbenchTabContextDTO(
            **{
                **current.__dict__,
                "versions": [*internal_versions, internal_version],
                "active_version_name": internal_version_name,
                "internal_parent_byte_overlays": parent_mapped,
                "module_paths": dict(current.module_paths) if current.workspace_path else {},
                "version_dirty": True,
            }
        )
        saved_internal = self._workspace_repository.save_tab_workspace(updated_internal, path)
        saved_internal = self._with_symbol_offsets(saved_internal)
        self._replace_context(saved_internal.tab_id, saved_internal)

        parent_version_name = (
            parent.active_version_name or BINARY_WORKBENCH_DEFAULT_VERSION_NAME
        )
        parent_version = self._version_from_current(parent_version_name, parent)
        parent_versions = [
            version
            for version in parent.versions
            if version.name != parent_version_name
        ]
        parent = BinaryWorkbenchTabContextDTO(
            **{
                **parent.__dict__,
                "versions": [*parent_versions, parent_version],
                "active_version_name": parent_version_name,
                "version_dirty": True,
            }
        )
        updated_parent = self._workspace_repository.save_tab_workspace(parent, None)
        self._remember_workspace_for_source(updated_parent)
        updated_parent = self._with_symbol_offsets(updated_parent)
        self._replace_context(updated_parent.tab_id, updated_parent)
        self._mark_page_context_stale(updated_parent)
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

    def _apply_matching_internal_workspace(
        self,
        context: BinaryWorkbenchTabContextDTO,
        path: Path,
        start_lba: int,
    ) -> BinaryWorkbenchTabContextDTO:
        manifest = self._workspace_repository.find_for_source(
            path,
            internal_file_start_lba=start_lba,
        )
        if manifest is None:
            return context
        return self._with_symbol_offsets(
            self._workspace_repository.load_tab_workspace(context, manifest)
        )

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
        if workspace_heavy_context_unloaded(context):
            return False
        current = self._workspace_repository.checksums_for_tab(context)
        if context.module_checksums:
            return any(current.get(key) != value for key, value in context.module_checksums.items())
        return any(
            (
                context.variables,
                context.equates,
                context.internal_files,
                any(
                    version.rows
                    or version.instruction_overlays
                    or version.instructions_by_line
                    or version.symbols_loaded
                    or version.variables
                    or version.equates
                    for version in context.versions
                ),
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
        labels = merged_instruction_labels(rows, context.instruction_overlays)
        labels = labels or context.labels
        symbol_rows = [*rows, *rows_from_overlays(context.instruction_overlays)]
        return BinaryWorkbenchTabContextDTO(
            **{
                **context.__dict__,
                "rows": rows,
                "labels": labels,
                "symbol_offsets": symbol_offsets(
                    symbol_rows,
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


def _internal_workspace_mapper(
    context: BinaryWorkbenchTabContextDTO,
) -> InternalOffsetMapper | None:
    if not context.source_path or context.internal_file_start_lba is None:
        return None
    source = Path(context.source_path)
    target = next(
        (
            item
            for item in context.internal_files
            if item.start_lba == context.internal_file_start_lba
        ),
        None,
    )
    if target is None or not source.exists():
        return None
    return InternalOffsetMapper(
        define_internal_file_region(
            source,
            target,
            context.internal_files,
            context.lba_sector_size,
        )
    )
