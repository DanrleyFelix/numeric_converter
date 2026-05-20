from pathlib import Path

from src.core.binary_workbench.file_ops import (
    build_version_rows_from_overlay,
    save_binary_as_assembly,
    save_versioned_binary,
)
from src.modules.dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_STATE,
    BINARY_WORKBENCH_TAB_KIND,
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
        if current is None or current.kind == BINARY_WORKBENCH_TAB_KIND.BINARY:
            return False
        if not current.source_path:
            return False
        target = Path(current.source_path)
        if not is_assembly_path(target):
            return False
        page = self.currentWidget()
        rows = page.grid.export_rows() if isinstance(page, BinaryWorkbenchEditorPage) else current.rows
        target.write_text(self._current_assembly_text(current), encoding="utf-8")
        self._remember_file_path(BINARY_WORKBENCH_STATE.SAVE_ASSEMBLY_DIRECTORY, target)
        self._set_current_context(BinaryWorkbenchTabContextDTO(**{**current.__dict__, "rows": rows, "original_rows": rows}))
        return True

    def _current_assembly_text(self, current: BinaryWorkbenchTabContextDTO) -> str:
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            return page.assembly_text()
        return "\n".join(row.instruction for row in current.rows)

    def _adopt_assembly_source(self, current: BinaryWorkbenchTabContextDTO, target: Path) -> None:
        page = self.currentWidget()
        rows = page.grid.export_rows() if isinstance(page, BinaryWorkbenchEditorPage) else current.rows
        self._set_current_context(
            BinaryWorkbenchTabContextDTO(
                **{
                    **current.__dict__,
                    "kind": BINARY_WORKBENCH_TAB_KIND.ASSEMBLY,
                    "display_name": target.name,
                    "source_path": str(target),
                    "read_mode": "assembly",
                    "rows": rows,
                    "original_rows": rows,
                }
            )
        )
