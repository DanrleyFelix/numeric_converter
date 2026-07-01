from pathlib import Path

from src.core.binary_workbench.internal_file_patch import patches_from_overlays
from src.core.binary_workbench.internal_file_reader import InternalFileView
from src.core.binary_workbench.internal_file_region import define_internal_file_region
from src.core.binary_workbench.internal_versioned_binary_saver import (
    save_internal_versioned_binary,
)
from src.core.binary_workbench.file_ops import (
    build_version_rows_from_overlay,
    save_binary_as_assembly,
    save_versioned_binary,
)
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_DEFAULT_VERSION_NAME,
    BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES,
    BINARY_WORKBENCH_STATE,
    BINARY_WORKBENCH_TAB_KIND,
)
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchVersionDTO,
)
from src.presentation.ui.components.binary_workbench.editor import BinaryWorkbenchEditorPage
from src.presentation.ui.components.binary_workbench.tabs.factory import is_assembly_path
from src.presentation.ui.components.binary_workbench.tabs.tab_state_payload import rows_to_bytes


class TabFileSavingMixin:
    def save_current_binary_copy(self, output_path: Path) -> bool:
        current = self.current_context()
        if current is None:
            return False
        if current.kind == BINARY_WORKBENCH_TAB_KIND.BINARY:
            if not current.source_path or not current.active_version_name:
                return False
            rows = build_version_rows_from_overlay(current.byte_overlays, list(current.reference_offsets), dict(current.reference_offset_bases))
            save_versioned_binary(Path(current.source_path), output_path, rows)
        elif current.kind == BINARY_WORKBENCH_TAB_KIND.INTERNAL:
            if not current.source_path or current.internal_file_start_lba is None:
                return False
            target = next(
                (
                    item
                    for item in current.internal_files
                    if item.start_lba == current.internal_file_start_lba
                ),
                None,
            )
            if target is None:
                return False
            region = define_internal_file_region(
                Path(current.source_path),
                target,
                current.internal_files,
                current.lba_sector_size,
            )
            view = InternalFileView(
                region,
                self._preferences.block_size,
                self._preferences.cache_max_blocks,
            )
            patches = patches_from_overlays(view, current.byte_overlays)
            save_internal_versioned_binary(region, output_path, patches)
        else:
            output_path.write_bytes(rows_to_bytes(current.rows))
        self._remember_file_path(BINARY_WORKBENCH_STATE.SAVE_FILE_DIRECTORY, output_path)
        return True

    def save_current_assembly_copy(self, output_path: Path, adopt_source: bool = False) -> bool:
        current = self.current_context()
        if current is None:
            return False
        target = output_path if output_path.suffix.lower() == ".asm" else output_path.with_suffix(".asm")
        if current.kind == BINARY_WORKBENCH_TAB_KIND.BINARY and current.source_path:
            save_binary_as_assembly(
                Path(current.source_path),
                target,
                self._preferences.block_size,
                self._preferences.cache_max_blocks,
                current.byte_overlays,
            )
        else:
            target.write_text(self._current_assembly_text(current), encoding="utf-8")
            if adopt_source:
                self._adopt_assembly_source(current, target)
        self._remember_file_path(BINARY_WORKBENCH_STATE.SAVE_ASSEMBLY_DIRECTORY, target)
        return True

    def save_current_source_file(self) -> bool:
        current = self.current_context()
        if current is None or current.kind in {
            BINARY_WORKBENCH_TAB_KIND.BINARY,
            BINARY_WORKBENCH_TAB_KIND.INTERNAL,
        }:
            return False
        if not current.source_path:
            return False
        target = Path(current.source_path)
        if not is_assembly_path(target):
            return False
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.commit_current_editor_text()
            current = page.current_context()
            rows = page.grid.export_rows()
            assembly_text = page.assembly_text()
        else:
            rows = current.rows
            assembly_text = self._current_assembly_text(current)
        target.write_text(assembly_text, encoding="utf-8")
        self._remember_file_path(BINARY_WORKBENCH_STATE.SAVE_ASSEMBLY_DIRECTORY, target)
        updated = BinaryWorkbenchTabContextDTO(
            **{
                **current.__dict__,
                "rows": rows,
                "original_rows": rows,
                "file_size": len(rows) * ROW_BYTES,
                "original_file_size": len(rows) * ROW_BYTES,
            }
        )
        self._replace_context(updated.tab_id, updated)
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.replace_context(updated)
        return True

    def _current_assembly_text(self, current: BinaryWorkbenchTabContextDTO) -> str:
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.commit_current_editor_text()
            return page.assembly_text()
        return "\n".join(row.instruction for row in current.rows)

    def _adopt_assembly_source(self, current: BinaryWorkbenchTabContextDTO, target: Path) -> None:
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            current = page.current_context()
            rows = page.grid.export_rows()
        else:
            rows = current.rows
        versions = current.versions or [
            BinaryWorkbenchVersionDTO(name=BINARY_WORKBENCH_DEFAULT_VERSION_NAME)
        ]
        updated = BinaryWorkbenchTabContextDTO(
            **{
                **current.__dict__,
                "kind": BINARY_WORKBENCH_TAB_KIND.ASSEMBLY,
                "display_name": target.name,
                "source_path": str(target),
                "read_mode": "assembly",
                "rows": rows,
                "original_rows": rows,
                "file_size": len(rows) * ROW_BYTES,
                "original_file_size": len(rows) * ROW_BYTES,
                "versions": versions,
                "active_version_name": current.active_version_name or versions[0].name,
            }
        )
        self._replace_context(updated.tab_id, updated)
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.replace_context(updated)
