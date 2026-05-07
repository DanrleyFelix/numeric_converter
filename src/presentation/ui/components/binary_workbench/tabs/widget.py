from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QPushButton, QTabBar, QTabWidget

from src.core.binary_workbench.file_ops import (
    apply_version_rows,
    build_version_rows_from_overlay,
    extract_internal_file_bytes,
    overlay_from_version_rows,
    save_binary_as_assembly,
    save_versioned_binary,
)
from src.core.binary_workbench.mips_r3000a import rebuild_rows_with_offsets
from src.modules.dtos import (
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchVersionDTO,
    BinaryWorkbenchViewPreferencesDTO,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_STATE,
    BINARY_WORKBENCH_TAB_KIND,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.editor import BinaryWorkbenchEditorPage
from src.presentation.ui.components.binary_workbench.tabs.factory import (
    create_assembly_tab,
    create_binary_tab,
    create_file_tab,
    create_internal_tab,
    create_scratch_tab,
    is_assembly_path,
    reload_source_rows,
    restorable_state,
)


class _BinaryWorkbenchTabBar(QTabBar):
    def tabSizeHint(self, index: int) -> QSize:
        return QSize(
            BINARY_WORKBENCH_LAYOUT.TAB_MAX_WIDTH,
            BINARY_WORKBENCH_LAYOUT.TAB_MIN_HEIGHT,
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_close_buttons()

    def tabLayoutChange(self) -> None:
        super().tabLayoutChange()
        self._position_close_buttons()

    def _position_close_buttons(self) -> None:
        for index in range(self.count()):
            button = self.tabButton(index, QTabBar.RightSide)
            if button is None:
                continue
            rect = self.tabRect(index)
            size = BINARY_WORKBENCH_LAYOUT.TAB_CLOSE_BUTTON_SIZE
            button.setFixedSize(size, size)
            button.move(rect.right() - size - 4, rect.top() + 2)


class BinaryWorkbenchTabs(QTabWidget):
    stateChanged = Signal(object)
    statusChanged = Signal(str)
    closeRequested = Signal(int)

    def __init__(self, state: BinaryWorkbenchStateDTO) -> None:
        super().__init__()
        self.setObjectName("binary-workbench-tabs")
        self.setTabBar(_BinaryWorkbenchTabBar())
        self.tabBar().setObjectName("binary-workbench-tab-bar")
        self.tabBar().setDrawBase(False)
        self.setTabsClosable(True)
        self.setDocumentMode(True)
        self._state = BinaryWorkbenchStateDTO()
        self.currentChanged.connect(self._sync_active_tab)
        self.tabCloseRequested.connect(self.closeRequested.emit)
        self.load_state(state)

    def export_state(self) -> BinaryWorkbenchStateDTO:
        return self._state

    def load_state(self, state: BinaryWorkbenchStateDTO) -> None:
        self.clear()
        self._state = restorable_state(state)
        for tab in self._state.tabs:
            self._add_tab_page(tab)
        if self.count():
            self.setCurrentIndex(self._active_index())
        self.stateChanged.emit(self._state)

    def open_binary_path(self, path: Path) -> None:
        self._remember_file_path(BINARY_WORKBENCH_STATE.OPEN_BINARY_DIRECTORY, path)
        self._append_tab(create_binary_tab(self._state, path))

    def open_file_path(self, path: Path) -> None:
        self._remember_file_path(BINARY_WORKBENCH_STATE.OPEN_FILE_DIRECTORY, path)
        self._append_tab(create_file_tab(self._state, path))

    def open_assembly_path(self, path: Path) -> None:
        self._remember_file_path(BINARY_WORKBENCH_STATE.OPEN_ASSEMBLY_DIRECTORY, path)
        self._append_tab(create_assembly_tab(self._state, path))

    def new_scratch_tab(self) -> None:
        self._append_tab(create_scratch_tab(self._state))

    def open_internal_tab(self, internal_name: str) -> None:
        current = self.current_context()
        if current is None or not current.source_path or not current.internal_files:
            self.statusChanged.emit(BINARY_WORKBENCH_TEXT.STATUS_INTERNAL_SOURCE_REQUIRED)
            return
        source = Path(current.source_path)
        target = next((item for item in current.internal_files if item.name == internal_name), None)
        if target is None:
            return
        data = extract_internal_file_bytes(source, target, current.internal_files)
        self._append_tab(create_internal_tab(self._state, current, target, data))

    def set_current_cpu_arch(self, value: str) -> None:
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.set_cpu_arch(value)

    def set_current_advanced_config(
        self,
        cpu_arch: str,
        read_mode: str,
        block_size: int,
        cache_max_blocks: int,
    ) -> None:
        current = self.current_context()
        if current is None:
            return
        updates: dict[str, object] = {
            "cpu_arch": cpu_arch,
            "read_mode": read_mode,
            "block_size": block_size,
            "cache_max_blocks": cache_max_blocks,
        }
        if current.source_path and current.kind in {BINARY_WORKBENCH_TAB_KIND.BINARY, BINARY_WORKBENCH_TAB_KIND.ASSEMBLY}:
            rows = reload_source_rows(
                Path(current.source_path),
                read_mode,
                current.reference_offsets,
                block_size,
                current.reference_offset_bases,
            )
            updates["original_rows"] = rows
            updates["rows"] = rows
        self._set_current_context(BinaryWorkbenchTabContextDTO(**{**current.__dict__, **updates}))

    def set_current_group_bytes(self, value: int) -> None:
        current = self.current_context()
        if current is None:
            return
        preferences = BinaryWorkbenchViewPreferencesDTO(
            visible_columns=dict(current.view_preferences.visible_columns),
            decoded_text_tables=list(current.view_preferences.decoded_text_tables),
            group_bytes=value,
        )
        updated = BinaryWorkbenchTabContextDTO(
            **{**current.__dict__, "view_preferences": preferences}
        )
        self._set_current_context(updated)

    def set_current_read_mode(self, value: str) -> None:
        current = self.current_context()
        if current is None:
            return
        updates: dict[str, object] = {"read_mode": value}
        if current.source_path and current.kind in {BINARY_WORKBENCH_TAB_KIND.BINARY, BINARY_WORKBENCH_TAB_KIND.ASSEMBLY}:
            original_rows = reload_source_rows(
                Path(current.source_path),
                value,
                current.reference_offsets,
                current.block_size,
                current.reference_offset_bases,
            )
            rows = original_rows
            if current.kind == BINARY_WORKBENCH_TAB_KIND.BINARY and current.active_version_name:
                version = next((item for item in current.versions if item.name == current.active_version_name), None)
                if version is not None:
                    rows = apply_version_rows(original_rows, version.rows)
            updates["original_rows"] = original_rows
            updates["rows"] = rows
        updated = BinaryWorkbenchTabContextDTO(**{**current.__dict__, **updates})
        self._set_current_context(updated)

    def set_current_internal_files(self, internal_files: list[BinaryWorkbenchInternalFileDTO]) -> None:
        current = self.current_context()
        if current is None:
            return
        updated = BinaryWorkbenchTabContextDTO(**{**current.__dict__, "internal_files": internal_files})
        self._set_current_context(updated)

    def set_current_symbols(
        self,
        variables: dict[str, str],
        equates: dict[str, str],
        labels: dict[str, str],
    ) -> None:
        current = self.current_context()
        if current is None:
            return
        page = self.currentWidget()
        rows = page.grid.export_rows() if isinstance(page, BinaryWorkbenchEditorPage) else current.rows
        updated = BinaryWorkbenchTabContextDTO(
            **{
                **current.__dict__,
                "variables": variables,
                "equates": equates,
                "labels": labels,
                "rows": rows,
                "symbol_offsets": _symbol_offsets(rows, variables, equates, labels),
            }
        )
        self._set_current_context(updated)

    def create_version(self, name: str) -> bool:
        current = self.current_context()
        if current is None or current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY:
            return False
        version = BinaryWorkbenchVersionDTO(
            name=name,
            rows=build_version_rows_from_overlay(
                current.byte_overlays,
                list(current.reference_offsets),
                dict(current.reference_offset_bases),
            ),
        )
        versions = [item for item in current.versions if item.name != name]
        updated = BinaryWorkbenchTabContextDTO(**{**current.__dict__, "versions": [*versions, version], "active_version_name": name})
        self._set_current_context(updated)
        return True

    def update_current_version(self, name: str) -> bool:
        current = self.current_context()
        if current is None or current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY or not current.active_version_name:
            return False
        version = BinaryWorkbenchVersionDTO(
            name=name,
            rows=build_version_rows_from_overlay(
                current.byte_overlays,
                list(current.reference_offsets),
                dict(current.reference_offset_bases),
            ),
        )
        versions = [item for item in current.versions if item.name != current.active_version_name]
        updated = BinaryWorkbenchTabContextDTO(**{**current.__dict__, "versions": [*versions, version], "active_version_name": name})
        self._set_current_context(updated)
        return True

    def load_version(self, name: str) -> bool:
        current = self.current_context()
        if current is None or current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY:
            return False
        version = next((item for item in current.versions if item.name == name), None)
        if version is None:
            return False
        rows = apply_version_rows(current.original_rows, version.rows)
        updated = BinaryWorkbenchTabContextDTO(
            **{
                **current.__dict__,
                "rows": rows,
                "byte_overlays": overlay_from_version_rows(version.rows),
                "active_version_name": name,
            }
        )
        self._set_current_context(updated)
        return True

    def save_current_binary_copy(self, output_path: Path) -> bool:
        current = self.current_context()
        if current is None:
            return False
        if current.kind == BINARY_WORKBENCH_TAB_KIND.BINARY:
            if not current.source_path or not current.active_version_name:
                return False
            version_rows = build_version_rows_from_overlay(
                current.byte_overlays,
                list(current.reference_offsets),
                dict(current.reference_offset_bases),
            )
            save_versioned_binary(Path(current.source_path), output_path, version_rows)
        else:
            output_path.write_bytes(_rows_to_bytes(current.rows))
        self._remember_file_path(BINARY_WORKBENCH_STATE.SAVE_FILE_DIRECTORY, output_path)
        return True

    def save_current_assembly_copy(self, output_path: Path) -> bool:
        current = self.current_context()
        if current is None:
            return False
        target = output_path if output_path.suffix.lower() == ".asm" else output_path.with_suffix(".asm")
        if current.kind == BINARY_WORKBENCH_TAB_KIND.BINARY and current.source_path:
            save_binary_as_assembly(
                Path(current.source_path),
                target,
                current.block_size,
                current.cache_max_blocks,
                current.byte_overlays,
            )
        else:
            target.write_text(self._current_assembly_text(current), encoding="utf-8")
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
        target.write_text(self._current_assembly_text(current), encoding="utf-8")
        self._remember_file_path(BINARY_WORKBENCH_STATE.SAVE_ASSEMBLY_DIRECTORY, target)
        return True

    def set_current_reference_offsets(
        self,
        reference_offsets: list[str],
        reference_offset_bases: dict[str, str],
        visible_columns: dict[str, bool],
    ) -> None:
        current = self.current_context()
        if current is None:
            return
        preferences = BinaryWorkbenchViewPreferencesDTO(
            visible_columns={
                **current.view_preferences.visible_columns,
                **visible_columns,
                "File": True,
                BINARY_WORKBENCH_TEXT.BYTES: True,
                BINARY_WORKBENCH_TEXT.INSTRUCTION: True,
            },
            decoded_text_tables=list(current.view_preferences.decoded_text_tables),
            group_bytes=current.view_preferences.group_bytes,
        )
        rows = rebuild_rows_with_offsets(
            current.rows,
            reference_offsets,
            reference_offset_bases,
        )
        updated = BinaryWorkbenchTabContextDTO(
            **{
                **current.__dict__,
                "reference_offsets": reference_offsets,
                "reference_offset_bases": reference_offset_bases,
                "rows": rows,
                "view_preferences": preferences,
            }
        )
        self._set_current_context(updated)

    def go_to_offset(self, offset: int) -> None:
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.go_to_offset(offset)

    def select_block(self, start_offset: int, end_offset: int) -> None:
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.select_block(start_offset, end_offset)

    def select_all_content(self) -> None:
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.select_all_content()

    def find_text(self, mode: str, query: str) -> bool:
        results = self.find_offsets(mode, query)
        page = self.currentWidget()
        if results and isinstance(page, BinaryWorkbenchEditorPage):
            page.go_to_offset(results[0])
        return bool(results)

    def find_offsets(self, mode: str, query: str) -> list[int]:
        page = self.currentWidget()
        if not isinstance(page, BinaryWorkbenchEditorPage):
            return []
        results = page.find_offsets(mode, query)
        self._cache_search_results(mode, query, results)
        return results

    def focused_editor_kind(self) -> str | None:
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            return page.focused_editor_kind()
        return None

    def directory_for(self, action_key: str) -> str:
        return self._state.directories.get(action_key, "")

    def current_context(self) -> BinaryWorkbenchTabContextDTO | None:
        index = self.currentIndex()
        return self._state.tabs[index] if 0 <= index < len(self._state.tabs) else None

    def context_at(self, index: int) -> BinaryWorkbenchTabContextDTO | None:
        return self._state.tabs[index] if 0 <= index < len(self._state.tabs) else None

    def has_unsaved_changes(self, index: int) -> bool:
        context = self.context_at(index)
        if context is None:
            return False
        if context.kind == BINARY_WORKBENCH_TAB_KIND.BINARY:
            return bool(context.byte_overlays)
        return context.rows != context.original_rows

    def _append_tab(self, context: BinaryWorkbenchTabContextDTO) -> None:
        self._state = BinaryWorkbenchStateDTO(
            tabs=[*self._state.tabs, context],
            active_tab_id=context.tab_id,
            share_view_preferences=self._state.share_view_preferences,
            recent_files=list(self._state.recent_files),
            directories=dict(self._state.directories),
        )
        self._add_tab_page(context)
        self.setCurrentIndex(self.count() - 1)
        self.statusChanged.emit(BINARY_WORKBENCH_TEXT.STATUS_OPENED_TEMPLATE.format(name=context.display_name))
        self.stateChanged.emit(self._state)

    def _add_tab_page(self, context: BinaryWorkbenchTabContextDTO) -> None:
        page = BinaryWorkbenchEditorPage(context)
        page.contextChanged.connect(lambda updated, tab_id=context.tab_id: self._replace_context(tab_id, updated))
        index = self.addTab(page, _tab_text(context.display_name))
        self.setTabToolTip(index, context.display_name)
        self.tabBar().setTabButton(index, QTabBar.RightSide, self._close_button(page))

    def close_tab(self, index: int) -> None:
        if not 0 <= index < len(self._state.tabs):
            return
        closed = self._state.tabs[index]
        remaining = [tab for idx, tab in enumerate(self._state.tabs) if idx != index]
        self.removeTab(index)
        self._state = BinaryWorkbenchStateDTO(
            tabs=remaining,
            active_tab_id=remaining[min(index, len(remaining) - 1)].tab_id if remaining else None,
            share_view_preferences=self._state.share_view_preferences,
            recent_files=list(self._state.recent_files),
            directories=dict(self._state.directories),
        )
        self.statusChanged.emit(BINARY_WORKBENCH_TEXT.STATUS_CLOSED_TEMPLATE.format(name=closed.display_name))
        self.stateChanged.emit(self._state)

    def _replace_context(self, tab_id: str, context: object) -> None:
        if not isinstance(context, BinaryWorkbenchTabContextDTO):
            return
        self._state = BinaryWorkbenchStateDTO(
            tabs=[context if tab.tab_id == tab_id else tab for tab in self._state.tabs],
            active_tab_id=self._state.active_tab_id,
            share_view_preferences=self._state.share_view_preferences,
            recent_files=list(self._state.recent_files),
            directories=dict(self._state.directories),
        )
        self.stateChanged.emit(self._state)

    def _set_current_context(self, context: BinaryWorkbenchTabContextDTO) -> None:
        index = self.currentIndex()
        if not 0 <= index < len(self._state.tabs):
            return
        self._replace_context(context.tab_id, context)
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.load_context(context)

    def _sync_active_tab(self, index: int) -> None:
        if not 0 <= index < len(self._state.tabs):
            return
        self._state = BinaryWorkbenchStateDTO(
            tabs=self._state.tabs,
            active_tab_id=self._state.tabs[index].tab_id,
            share_view_preferences=self._state.share_view_preferences,
            recent_files=list(self._state.recent_files),
            directories=dict(self._state.directories),
        )
        self.stateChanged.emit(self._state)

    def _active_index(self) -> int:
        return next((idx for idx, tab in enumerate(self._state.tabs) if tab.tab_id == self._state.active_tab_id), 0)

    def _close_button(self, page: BinaryWorkbenchEditorPage) -> QPushButton:
        button = QPushButton("X", self.tabBar())
        button.setObjectName("binary-workbench-tab-close")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(lambda: self.closeRequested.emit(self.indexOf(page)))
        return button

    def _remember_file_path(self, action_key: str, path: Path) -> None:
        recent_files = [str(path), *[item for item in self._state.recent_files if item != str(path)]]
        self._state = BinaryWorkbenchStateDTO(
            tabs=self._state.tabs,
            active_tab_id=self._state.active_tab_id,
            share_view_preferences=self._state.share_view_preferences,
            recent_files=recent_files[: BINARY_WORKBENCH_STATE.RECENT_FILES_LIMIT],
            directories={**self._state.directories, action_key: str(path.parent)},
        )
        self.stateChanged.emit(self._state)

    def _cache_search_results(self, mode: str, query: str, results: list[int]) -> None:
        current = self.current_context()
        if current is None or not query:
            return
        key = f"{mode}:{query}"
        updated = BinaryWorkbenchTabContextDTO(
            **{
                **current.__dict__,
                "search_cache": {
                    **current.search_cache,
                    key: [f"0x{offset:08X}" for offset in results],
                },
            }
        )
        self._replace_context(current.tab_id, updated)

    def _current_assembly_text(self, current: BinaryWorkbenchTabContextDTO) -> str:
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            return page.assembly_text()
        return "\n".join(row.instruction for row in current.rows)


def _tab_text(value: str) -> str:
    if len(value) <= BINARY_WORKBENCH_LAYOUT.TAB_MAX_CHARACTERS:
        return value
    return f"{value[: BINARY_WORKBENCH_LAYOUT.TAB_MAX_CHARACTERS - 3]}..."


def _rows_to_bytes(rows: list[BinaryWorkbenchRowDTO]) -> bytes:
    return b"".join(bytes.fromhex(row.bytes_text.replace(" ", "")) for row in rows)


def _symbol_offsets(
    rows: list[BinaryWorkbenchRowDTO],
    variables: dict[str, str],
    equates: dict[str, str],
    labels: dict[str, str],
) -> dict[str, list[str]]:
    values = {name: [] for name in [*variables.keys(), *equates.keys(), *labels.keys()]}
    for row in rows:
        offset = row.offsets.get("File", "0x00000000")
        for name in variables:
            if f"_{name.lstrip('_')}" in row.instruction:
                values[name].append(offset)
        for name in equates:
            if f"@{name.lstrip('@')}" in row.instruction:
                values[name].append(offset)
    for name, offset in labels.items():
        values[name] = [offset]
    return values
