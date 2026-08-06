from copy import deepcopy
from pathlib import Path

from src.core.binary_workbench.codec_registry import binary_workbench_codec_for
from src.core.binary_workbench.context_overlays import compact_binary_context_overlays
from src.core.binary_workbench.file_ops import (
    apply_version_rows,
    build_version_rows_from_overlay,
    overlay_from_version_rows,
)
from src.core.binary_workbench.internal_version_rows import (
    build_internal_version_rows_from_overlay,
)
from src.core.binary_workbench.row_structure import valid_offset_end
from src.core.binary_workbench.version_overlays import (
    byte_overlays_from_instruction_overlays,
    without_blank_instruction_overlays,
)
from src.core.binary_workbench.persistence import normalize_locked_assembly_rows
from src.core.binary_workbench.version_instruction_maps import version_instruction_maps
from src.core.binary_workbench.version_line_comments import apply_line_comments
from src.core.binary_workbench.version_names import sorted_versions
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_DEFAULT_VERSION_NAME,
    BINARY_WORKBENCH_TAB_KIND,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO, BinaryWorkbenchVersionDTO
from src.presentation.repository.binary_workbench_workspace.constants import (
    VERSION_PATH_PREFIX,
    VERSIONS,
)
from src.presentation.ui.components.binary_workbench.editor import BinaryWorkbenchEditorPage
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    apply_instruction_overlays,
)
from src.presentation.ui.components.binary_workbench.tabs.autosave import (
    VersionAutosaveResult,
)


class TabVersionsMixin:
    def create_version(self, name: str) -> bool:
        if not self.ensure_current_consistent("create-version").success:
            return False
        current = self.current_context()
        if not self._is_versioned_context(current):
            return False
        current = compact_binary_context_overlays(current)
        version = self._version_from_current(name, current)
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.create_consistency_version(name)
        replaced_names = {name, current.active_version_name}
        versions = [item for item in current.versions if item.name not in replaced_names]
        if current.active_version_name and current.active_version_name != name:
            versions.append(self._version_from_current(current.active_version_name, current))
        self._set_current_context(
            BinaryWorkbenchTabContextDTO(**{**current.__dict__, "versions": _sorted_versions([*versions, version]), "active_version_name": name, "version_dirty": True})
        )
        return True

    def update_current_version(
        self,
        name: str,
        *,
        mark_dirty: bool = True,
        reload_page: bool = True,
        ensure_consistency: bool = True,
    ) -> bool:
        if ensure_consistency and not self.ensure_current_consistent("update-version").success:
            return False
        current = self.current_context()
        if not self._is_versioned_context(current) or not current.active_version_name:
            return False
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.commit_current_editor_text()
            current = page.current_context()
        current = compact_binary_context_overlays(current)
        previous_name = current.active_version_name
        version = self._version_from_current(name, current)
        versions = [item for item in current.versions if item.name != previous_name]
        updated = BinaryWorkbenchTabContextDTO(**{**current.__dict__, "versions": _sorted_versions([*versions, version]), "active_version_name": name, "version_dirty": mark_dirty})
        if isinstance(page, BinaryWorkbenchEditorPage) and previous_name != name:
            page.rename_consistency_version(previous_name, name)
        if reload_page:
            self._set_current_context(updated)
        else:
            self._set_current_context_without_page_reload(updated)
        return True

    def load_version(self, name: str) -> bool:
        if not self.ensure_current_consistent("load-version").success:
            return False
        current = self.current_context()
        if not self._is_versioned_context(current):
            return False
        if current.active_version_name and current.active_version_name != name:
            self.update_current_version(current.active_version_name)
            current = self.current_context()
            if current is None:
                return False

        current = compact_binary_context_overlays(current)
        version = self._version_for_load(current, name)
        if version is None:
            return False
        versions = [
            version if item.name == name else item
            for item in current.versions
        ]
        rows = self._rows_from_version(current, version)
        if current.kind == BINARY_WORKBENCH_TAB_KIND.ASSEMBLY and version.rows:
            byte_overlays = {}
            instruction_overlays = {}
        else:
            byte_overlays = overlay_from_version_rows(version.rows)
            instruction_overlays = self._instruction_overlays_from_version(current, version)
        variables = dict(current.variables)
        equates = dict(current.equates)
        if instruction_overlays:
            byte_overlays.update(
                byte_overlays_from_instruction_overlays(
                    instruction_overlays,
                    variables,
                    equates,
                )
            )
        byte_overlays, instruction_overlays = without_blank_instruction_overlays(
            byte_overlays,
            instruction_overlays,
        )
        updated = compact_binary_context_overlays(BinaryWorkbenchTabContextDTO(
            **{
                **current.__dict__,
                "rows": rows,
                "versions": _sorted_versions(versions),
                "read_mode": "assembly" if version.instructions_by_line else current.read_mode,
                "byte_overlays": byte_overlays,
                "instruction_overlays": instruction_overlays,
                "file_size": _version_file_size(current, rows, byte_overlays),
                "variables": variables,
                "equates": equates,
                "active_version_name": name,
                "version_dirty": False,
            }
        ))
        self._set_current_context(self._with_symbol_offsets(updated))
        return True

    def load_versions_file(self, path) -> str | None:
        current = self.current_context()
        if not self._is_versioned_context(current):
            return None
        path = Path(path)
        if hasattr(self._workspace_repository, "load_versions_file_with_active"):
            loaded, active = self._workspace_repository.load_versions_file_with_active(path)
        else:
            loaded = self._workspace_repository.load_versions_file(path)
            active = loaded[0].name if loaded else None
        if not loaded or active is None:
            return None
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.replace_consistency_versions([version.name for version in loaded])
        path = self.import_environment_file(VERSIONS, path)
        loaded = _versions_with_only_active_loaded(loaded, active)
        module_paths = {
            key: value
            for key, value in current.module_paths.items()
            if key != VERSIONS and not key.startswith(VERSION_PATH_PREFIX)
        }
        module_paths[VERSIONS] = str(path)
        module_paths.update({f"{VERSION_PATH_PREFIX}{version.name}": str(path) for version in loaded})
        self._set_current_context(
            BinaryWorkbenchTabContextDTO(
                **{
                    **current.__dict__,
                    "versions": _sorted_versions(loaded),
                    "active_version_name": active,
                    "module_paths": module_paths,
                    "module_directories": {
                        **current.module_directories,
                        "versions": str(self._workspace_repository.environment_directory(VERSIONS) or path.parent),
                    },
                }
            )
        )
        return active if self.load_version(active) else None

    def _version_for_load(
        self,
        current: BinaryWorkbenchTabContextDTO,
        name: str,
    ) -> BinaryWorkbenchVersionDTO | None:
        version = next((item for item in current.versions if item.name == name), None)
        if version is None:
            return None
        if _version_placeholder(version):
            loaded = self._workspace_repository.load_version_from_context(current, name)
            return loaded or version
        return version

    def _version_from_current(
        self,
        name: str,
        current: BinaryWorkbenchTabContextDTO,
    ) -> BinaryWorkbenchVersionDTO:
        """Build a version without legacy overlay work for Assembly sources."""

        current = compact_binary_context_overlays(current)
        if current.kind == BINARY_WORKBENCH_TAB_KIND.ASSEMBLY:
            rows = deepcopy(current.rows)
            if not self._preferences.assembly_edit_rules.allow_byte_shift:
                previous = next(
                    (
                        version.rows
                        for version in current.versions
                        if version.name == current.active_version_name
                    ),
                    [],
                )
                rows = normalize_locked_assembly_rows(
                    rows,
                    binary_workbench_codec_for(current.cpu_arch),
                    current.labels,
                    current.variables,
                    current.equates,
                    (previous, current.original_rows),
                )
            instruction_overlays = {}
            instructions_by_line = {}
        else:
            instruction_overlays, instructions_by_line = version_instruction_maps(
                current.rows,
                current.instruction_overlays,
                binary_workbench_codec_for(current.cpu_arch),
                current.labels,
                current.variables,
                current.equates,
            )
            rows = build_version_rows_from_overlay(
                current.byte_overlays,
                list(current.reference_offsets),
                dict(current.reference_offset_bases),
            )
        if (
            current.kind == BINARY_WORKBENCH_TAB_KIND.INTERNAL
            and current.source_path
            and current.internal_file_start_lba is not None
        ):
            rows = build_internal_version_rows_from_overlay(
                Path(current.source_path),
                current.internal_file_start_lba,
                current.internal_files,
                current.lba_sector_size,
                current.byte_overlays,
                list(current.reference_offsets),
                dict(current.reference_offset_bases),
                current.original_rows,
                current.rows,
            )
        return BinaryWorkbenchVersionDTO(
            name=name,
            rows=rows,
            instruction_overlays=instruction_overlays,
            instructions_by_line=instructions_by_line,
            variables={},
            equates={},
            symbols_loaded=False,
        )

    def backup_default_version_if_due(self) -> bool:
        current = self.current_context()
        if not self._is_versioned_context(current):
            return False
        count = self._version_update_counts.get(current.tab_id, 0) + 1
        self._version_update_counts[current.tab_id] = count
        if count % 3:
            return False
        default_version = self._version_from_current(
            BINARY_WORKBENCH_DEFAULT_VERSION_NAME,
            current,
        )
        versions = [
            version
            for version in current.versions
            if version.name != BINARY_WORKBENCH_DEFAULT_VERSION_NAME
        ]
        self._set_current_context_without_page_reload(
            BinaryWorkbenchTabContextDTO(
                **{
                    **current.__dict__,
                    "versions": _sorted_versions([*versions, default_version]),
                }
            )
        )
        return True

    def schedule_version_autosave(self, tab_id: str) -> bool:
        """Schedule an Assembly-only version save without a consistency barrier."""

        current = next(
            (tab for tab in self._state.tabs if tab.tab_id == tab_id),
            None,
        )
        if (
            current is None
            or current.kind != BINARY_WORKBENCH_TAB_KIND.ASSEMBLY
            or not current.active_version_name
        ):
            return False
        self._version_autosave.schedule(tab_id)
        return True

    def autosave_current_version_after_structure(self) -> bool:
        """Keep the former entry point as a deferred Assembly autosave adapter."""

        current = self.current_context()
        return bool(current and self.schedule_version_autosave(current.tab_id))

    def _version_autosave_snapshot(
        self,
        tab_id: str,
    ) -> BinaryWorkbenchTabContextDTO | None:
        """Capture only current Assembly rows and active-version metadata."""

        current = next(
            (tab for tab in self._state.tabs if tab.tab_id == tab_id),
            None,
        )
        if (
            current is None
            or current.kind != BINARY_WORKBENCH_TAB_KIND.ASSEMBLY
            or not current.active_version_name
        ):
            return None
        existing = next(
            (
                item
                for item in current.versions
                if item.name == current.active_version_name
            ),
            None,
        )
        version = BinaryWorkbenchVersionDTO(
            **{
                **(existing.__dict__ if existing is not None else {
                    "name": current.active_version_name,
                }),
                "rows": list(current.rows),
            }
        )
        versions = [
            version if item.name == version.name else item
            for item in current.versions
        ]
        if not any(item.name == version.name for item in current.versions):
            versions.append(version)
        snapshot = BinaryWorkbenchTabContextDTO(
            **{
                **current.__dict__,
                "versions": _sorted_versions(versions),
            }
        )
        self._replace_autosave_context(snapshot)
        return snapshot

    def _handle_version_autosave_saved(
        self,
        result: VersionAutosaveResult,
    ) -> None:
        """Merge persistence paths without replacing editor rows or projections."""

        current = next(
            (tab for tab in self._state.tabs if tab.tab_id == result.tab_id),
            None,
        )
        if current is None:
            return
        updated = BinaryWorkbenchTabContextDTO(
            **{
                **current.__dict__,
                "module_paths": result.module_paths,
                "version_dirty": (
                    current.version_dirty
                    if not self._version_autosave.is_current(
                        result.tab_id,
                        result.generation,
                    )
                    else False
                ),
            }
        )
        self._replace_autosave_context(updated)

    def _handle_version_autosave_failed(self, error: str) -> None:
        """Report a background autosave failure without interrupting editing."""

        self.statusWarningChanged.emit(
            BINARY_WORKBENCH_TEXT.STATUS_VERSION_AUTOSAVE_FAILED_TEMPLATE.format(
                error=error,
            )
        )

    def _replace_autosave_context(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> None:
        """Replace lightweight persistence state without reloading any editor."""

        self._replace_context_without_emit(context.tab_id, context)
        index = next(
            (
                item
                for item, tab in enumerate(self._state.tabs)
                if tab.tab_id == context.tab_id
            ),
            -1,
        )
        page = self.widget(index) if 0 <= index < self.count() else None
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.replace_persistence_context(context)

    def flush_version_autosave(self) -> None:
        """Flush pending Assembly snapshots without running an ALT+S barrier."""

        if not hasattr(self, "_version_autosave"):
            return
        self._version_autosave.flush_now()

    @staticmethod
    def _is_versioned_context(current: BinaryWorkbenchTabContextDTO | None) -> bool:
        return current is not None and (
            current.kind in {
                BINARY_WORKBENCH_TAB_KIND.BINARY,
                BINARY_WORKBENCH_TAB_KIND.INTERNAL,
            }
            or current.kind == BINARY_WORKBENCH_TAB_KIND.ASSEMBLY
            and bool(current.source_path)
            and Path(current.source_path).is_file()
        )

    def _rows_from_version(
        self,
        current: BinaryWorkbenchTabContextDTO,
        version: BinaryWorkbenchVersionDTO,
    ):
        if current.kind == BINARY_WORKBENCH_TAB_KIND.ASSEMBLY and version.rows:
            rows = deepcopy(version.rows)
        else:
            rows = apply_version_rows(current.original_rows, version.rows) if version.rows else (current.original_rows or current.rows)
        if version.instruction_overlays:
            rows = apply_instruction_overlays(rows, version.instruction_overlays)
        if not version.instructions_by_line:
            return rows
        return apply_line_comments(rows, version.instructions_by_line, list(current.reference_offsets))

    def _instruction_overlays_from_version(
        self,
        current: BinaryWorkbenchTabContextDTO,
        version: BinaryWorkbenchVersionDTO,
    ) -> dict[str, str]:
        if version.instructions_by_line:
            return {
                **version.instruction_overlays,
                **{
                    row.offsets.get("File", "0x00000000"): row.instruction
                    for row in self._rows_from_version(current, version)
                    if row.instruction and row.offsets.get("File") != "-"
                },
            }
        return dict(version.instruction_overlays)



def _version_file_size(
    current: BinaryWorkbenchTabContextDTO,
    rows: list,
    byte_overlays: dict[str, str],
) -> int:
    size = valid_offset_end(rows)
    if current.kind != BINARY_WORKBENCH_TAB_KIND.ASSEMBLY:
        size = max(size, current.original_file_size)
    for offset, bytes_text in byte_overlays.items():
        try:
            size = max(
                size,
                int(offset, 0) + (len(bytes_text.replace(" ", "")) // 2),
            )
        except ValueError:
            continue
    return size


def _sorted_versions(
    versions: list[BinaryWorkbenchVersionDTO],
) -> list[BinaryWorkbenchVersionDTO]:
    return sorted_versions(versions, name_of=lambda version: version.name)


def _version_placeholder(version: BinaryWorkbenchVersionDTO) -> bool:
    return (
        not version.rows
        and not version.instruction_overlays
        and not version.instructions_by_line
        and not version.symbols_loaded
    )


def _versions_with_only_active_loaded(
    versions: list[BinaryWorkbenchVersionDTO],
    active: str,
) -> list[BinaryWorkbenchVersionDTO]:
    return _sorted_versions([
        version if version.name == active else BinaryWorkbenchVersionDTO(name=version.name)
        for version in versions
    ])
