from pathlib import Path

from src.core.binary_workbench.file_ops import apply_version_rows
from src.core.binary_workbench.mips_r3000a import rebuild_rows_with_offsets
from src.modules.dtos import BinaryWorkbenchTabContextDTO, BinaryWorkbenchViewPreferencesDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TAB_KIND, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor import BinaryWorkbenchEditorPage
from src.presentation.ui.components.binary_workbench.tabs.factory import reload_source_rows


class TabConfigurationMixin:
    def set_current_cpu_arch(self, value: str) -> None:
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.set_cpu_arch(value)

    def set_current_advanced_config(self, cpu_arch: str, read_mode: str, block_size: int, cache_max_blocks: int) -> None:
        current = self.current_context()
        if current is None:
            return
        updates: dict[str, object] = {"cpu_arch": cpu_arch, "read_mode": read_mode, "block_size": block_size, "cache_max_blocks": cache_max_blocks}
        if current.source_path and current.kind in {BINARY_WORKBENCH_TAB_KIND.BINARY, BINARY_WORKBENCH_TAB_KIND.ASSEMBLY}:
            rows = reload_source_rows(Path(current.source_path), read_mode, current.reference_offsets, block_size, current.reference_offset_bases)
            updates.update({"original_rows": rows, "rows": rows})
        self._set_current_context(BinaryWorkbenchTabContextDTO(**{**current.__dict__, **updates}))

    def set_current_group_bytes(self, value: int) -> None:
        current = self.current_context()
        if current is not None:
            self.set_current_bytes_formatter(value, current.view_preferences.uppercase_bytes, current.view_preferences.uppercase_instructions)

    def set_current_bytes_formatter(self, group_bytes: int, uppercase_bytes: bool, uppercase_instructions: bool) -> None:
        current = self.current_context()
        if current is None:
            return
        preferences = BinaryWorkbenchViewPreferencesDTO(
            visible_columns=dict(current.view_preferences.visible_columns),
            decoded_text_tables=list(current.view_preferences.decoded_text_tables),
            group_bytes=group_bytes,
            uppercase_bytes=uppercase_bytes,
            uppercase_instructions=uppercase_instructions,
        )
        self._set_current_context(BinaryWorkbenchTabContextDTO(**{**current.__dict__, "view_preferences": preferences}))

    def set_current_read_mode(self, value: str) -> None:
        current = self.current_context()
        if current is None:
            return
        updates: dict[str, object] = {"read_mode": value}
        if current.source_path and current.kind in {BINARY_WORKBENCH_TAB_KIND.BINARY, BINARY_WORKBENCH_TAB_KIND.ASSEMBLY}:
            rows = reload_source_rows(Path(current.source_path), value, current.reference_offsets, current.block_size, current.reference_offset_bases)
            if current.kind == BINARY_WORKBENCH_TAB_KIND.BINARY and current.active_version_name:
                version = next((item for item in current.versions if item.name == current.active_version_name), None)
                rows = apply_version_rows(rows, version.rows) if version is not None else rows
            updates.update({"original_rows": rows, "rows": rows})
        self._set_current_context(BinaryWorkbenchTabContextDTO(**{**current.__dict__, **updates}))

    def set_current_reference_offsets(self, reference_offsets: list[str], reference_offset_bases: dict[str, str], visible_columns: dict[str, bool]) -> None:
        current = self.current_context()
        if current is None:
            return
        preferences = BinaryWorkbenchViewPreferencesDTO(
            visible_columns={**current.view_preferences.visible_columns, **visible_columns, "File": True, BINARY_WORKBENCH_TEXT.BYTES: True, BINARY_WORKBENCH_TEXT.INSTRUCTION: True},
            decoded_text_tables=list(current.view_preferences.decoded_text_tables),
            group_bytes=current.view_preferences.group_bytes,
            uppercase_bytes=current.view_preferences.uppercase_bytes,
            uppercase_instructions=current.view_preferences.uppercase_instructions,
        )
        rows = rebuild_rows_with_offsets(current.rows, reference_offsets, reference_offset_bases)
        self._set_current_context(BinaryWorkbenchTabContextDTO(**{**current.__dict__, "reference_offsets": reference_offsets, "reference_offset_bases": reference_offset_bases, "rows": rows, "view_preferences": preferences}))
