from dataclasses import replace
from pathlib import Path

from src.core.binary_workbench.internal_file_patch import (
    binary_overlays_from_internal_overlays,
)
from src.core.binary_workbench.internal_file_region import define_internal_file_region
from src.core.binary_workbench.internal_offset_mapper import InternalOffsetMapper
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_TAB_KIND
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor import BinaryWorkbenchEditorPage
from src.presentation.ui.components.binary_workbench.tabs.factory import restorable_state
from src.presentation.ui.components.binary_workbench.tabs.tab_state_payload import state_payload, tab_text
from src.presentation.ui.components.binary_workbench.tabs.tab_workspace import DIRECTORY_KEYS

TRANSIENT_VISIBLE_CONTEXT_FIELDS = {
    "rows",
    "labels",
    "symbol_offsets",
    "last_open_offset",
    "file_size",
    "original_file_size",
}


class TabStateMixin:
    def export_state(self) -> BinaryWorkbenchStateDTO:
        return self._state

    def load_state(self, state: BinaryWorkbenchStateDTO) -> None:
        self.clear()
        self._stale_context_pages.clear()
        self._state = restorable_state(state)
        for tab in self._state.tabs:
            self._add_tab_page(tab)
        if self.count():
            self.setCurrentIndex(self._active_index())
        self.stateChanged.emit(self._state)

    def directory_for(self, action_key: str) -> str:
        if value := self._state.directories.get(action_key, ""):
            return value
        return self.workspace_module_directory(action_key)

    def set_directory(self, action_key: str, path: Path) -> None:
        module_key = DIRECTORY_KEYS.get(action_key)
        current = self.current_context()
        if module_key and current is not None:
            current = BinaryWorkbenchTabContextDTO(
                **{
                    **current.__dict__,
                    "module_directories": {
                        **current.module_directories,
                        module_key: str(path),
                    },
                }
            )
            self._replace_context(current.tab_id, current)
        self._state = BinaryWorkbenchStateDTO(
            **{**state_payload(self._state), "directories": {**self._state.directories, action_key: str(path)}}
        )
        self.stateChanged.emit(self._state)

    def current_context(self) -> BinaryWorkbenchTabContextDTO | None:
        index = self.currentIndex()
        return self._state.tabs[index] if 0 <= index < len(self._state.tabs) else None

    def context_at(self, index: int) -> BinaryWorkbenchTabContextDTO | None:
        return self._state.tabs[index] if 0 <= index < len(self._state.tabs) else None

    def has_unsaved_changes(self, index: int) -> bool:
        context = self.context_at(index)
        if context is None:
            return False
        if context.kind == BINARY_WORKBENCH_TAB_KIND.INTERNAL:
            mapper = _internal_mapper(context)
            if mapper is None:
                return self.has_unsaved_version_edits(context)
            return (
                binary_overlays_from_internal_overlays(
                    mapper,
                    context.byte_overlays,
                )
                != context.internal_parent_byte_overlays
            )
        if context.kind == "binary":
            return self.has_unsaved_version_edits(context) or self._has_workspace_module_changes(context)
        return self._controller.rows_have_unsaved_edits(
            context.rows,
            context.original_rows,
        ) or self._has_workspace_module_changes(context)

    def close_tab(self, index: int) -> None:
        if not 0 <= index < len(self._state.tabs):
            return
        closed = self._state.tabs[index]
        remaining = [tab for idx, tab in enumerate(self._state.tabs) if idx != index]
        self.removeTab(index)
        active = remaining[min(index, len(remaining) - 1)].tab_id if remaining else None
        self._state = BinaryWorkbenchStateDTO(**{**state_payload(self._state), "tabs": remaining, "active_tab_id": active})
        self.statusChanged.emit(BINARY_WORKBENCH_TEXT.STATUS_CLOSED_TEMPLATE.format(name=closed.display_name))
        self.stateChanged.emit(self._state)

    def _append_tab(self, context: BinaryWorkbenchTabContextDTO) -> None:
        self._state = BinaryWorkbenchStateDTO(
            **{**state_payload(self._state), "tabs": [*self._state.tabs, context], "active_tab_id": context.tab_id}
        )
        self._add_tab_page(context)
        self.setCurrentIndex(self.count() - 1)
        self.statusChanged.emit(BINARY_WORKBENCH_TEXT.STATUS_OPENED_TEMPLATE.format(name=context.display_name))
        self.stateChanged.emit(self._state)

    def _replace_context(self, tab_id: str, context: object) -> None:
        if not isinstance(context, BinaryWorkbenchTabContextDTO):
            return
        tabs = [context if tab.tab_id == tab_id else tab for tab in self._state.tabs]
        self._state = BinaryWorkbenchStateDTO(**{**state_payload(self._state), "tabs": tabs})
        self._refresh_tab_label(tab_id, context.display_name)
        self.stateChanged.emit(self._state)

    def _handle_page_context_change(self, tab_id: str, context: object) -> None:
        if not isinstance(context, BinaryWorkbenchTabContextDTO):
            return
        previous = next((tab for tab in self._state.tabs if tab.tab_id == tab_id), None)
        if previous is not None and _is_transient_visible_context_update(previous, context):
            self._replace_context_without_emit(tab_id, context)
            return
        if previous is None or context.kind != BINARY_WORKBENCH_TAB_KIND.INTERNAL:
            self._replace_context(tab_id, context)
            return
        parent = self._internal_parent_context(context)
        mapper = _internal_mapper(context)
        if parent is None or mapper is None:
            self._replace_context(tab_id, context)
            return
        previous_mapped = binary_overlays_from_internal_overlays(
            mapper,
            previous.byte_overlays,
        )
        current_mapped = binary_overlays_from_internal_overlays(
            mapper,
            context.byte_overlays,
        )
        controlled_offsets = {
            *previous_mapped,
            *context.internal_parent_byte_overlays,
        }
        if (
            previous.byte_overlays == context.byte_overlays
            and all(
                parent.byte_overlays.get(offset) == value
                for offset, value in current_mapped.items()
            )
            and all(
                offset in current_mapped or offset not in parent.byte_overlays
                for offset in controlled_offsets
            )
        ):
            self._replace_context(
                tab_id,
                replace(context, internal_parent_tab_id=parent.tab_id),
            )
            return
        parent_overlays = dict(parent.byte_overlays)
        for offset in controlled_offsets:
            parent_overlays.pop(offset, None)
        parent_overlays.update(current_mapped)
        parent_overlays_changed = parent_overlays != parent.byte_overlays
        parent = replace(
            parent,
            byte_overlays=parent_overlays,
            version_dirty=parent.version_dirty or parent_overlays_changed,
        )
        context = replace(context, internal_parent_tab_id=parent.tab_id)
        tabs = [
            context if tab.tab_id == tab_id else parent if tab.tab_id == parent.tab_id else tab
            for tab in self._state.tabs
        ]
        self._state = BinaryWorkbenchStateDTO(
            **{**state_payload(self._state), "tabs": tabs}
        )
        self._refresh_tab_label(tab_id, context.display_name)
        self._mark_page_context_stale(parent)
        self.stateChanged.emit(self._state)

    def discard_internal_changes(self, index: int) -> bool:
        context = self.context_at(index)
        if context is None or context.kind != BINARY_WORKBENCH_TAB_KIND.INTERNAL:
            return False
        parent = self._internal_parent_context(context)
        mapper = _internal_mapper(context)
        if parent is None or mapper is None:
            return False
        current_mapped = binary_overlays_from_internal_overlays(
            mapper,
            context.byte_overlays,
        )
        parent_overlays = dict(parent.byte_overlays)
        for offset in current_mapped:
            parent_overlays.pop(offset, None)
        parent_overlays.update(context.internal_parent_byte_overlays)
        parent = replace(parent, byte_overlays=parent_overlays)
        parent = replace(
            parent,
            version_dirty=self._controller.version_has_unsaved_edits(parent),
        )
        tabs = [parent if tab.tab_id == parent.tab_id else tab for tab in self._state.tabs]
        self._state = BinaryWorkbenchStateDTO(
            **{**state_payload(self._state), "tabs": tabs}
        )
        self._mark_page_context_stale(parent)
        self.stateChanged.emit(self._state)
        return True

    def _internal_parent_context(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> BinaryWorkbenchTabContextDTO | None:
        if context.internal_parent_tab_id:
            parent = next(
                (
                    tab
                    for tab in self._state.tabs
                    if tab.tab_id == context.internal_parent_tab_id
                ),
                None,
            )
            if parent is not None:
                return parent
        return next(
            (
                tab
                for tab in self._state.tabs
                if tab.kind == BINARY_WORKBENCH_TAB_KIND.BINARY
                and tab.source_path == context.source_path
            ),
            None,
        )

    def _mark_page_context_stale(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> None:
        index = next(
            (
                index
                for index, tab in enumerate(self._state.tabs)
                if tab.tab_id == context.tab_id
            ),
            -1,
        )
        page = self.widget(index) if index >= 0 else None
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.replace_context(context)
            self._stale_context_pages.add(context.tab_id)

    def _set_current_context(self, context: BinaryWorkbenchTabContextDTO) -> None:
        index = self.currentIndex()
        if not 0 <= index < len(self._state.tabs):
            return
        self._replace_context(context.tab_id, context)
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.set_preferences(self._preferences)
            page.load_context(context)

    def _replace_context_without_emit(
        self,
        tab_id: str,
        context: BinaryWorkbenchTabContextDTO,
    ) -> None:
        self._state = BinaryWorkbenchStateDTO(
            **{
                **state_payload(self._state),
                "tabs": [
                    context if tab.tab_id == tab_id else tab
                    for tab in self._state.tabs
                ],
            }
        )

    def _sync_active_tab(self, index: int) -> None:
        if not 0 <= index < len(self._state.tabs):
            return
        self._state = BinaryWorkbenchStateDTO(**{**state_payload(self._state), "active_tab_id": self._state.tabs[index].tab_id})
        context = self._state.tabs[index]
        if context.tab_id in self._stale_context_pages:
            self._stale_context_pages.discard(context.tab_id)
            page = self.widget(index)
            if isinstance(page, BinaryWorkbenchEditorPage):
                page.load_context(context)
        self.stateChanged.emit(self._state)

    def _sync_tab_order(self, source: int, target: int) -> None:
        if not 0 <= source < len(self._state.tabs) or not 0 <= target < len(self._state.tabs):
            return
        tabs = list(self._state.tabs)
        context = tabs.pop(source)
        tabs.insert(target, context)
        self._state = BinaryWorkbenchStateDTO(
            **{**state_payload(self._state), "tabs": tabs}
        )
        self.stateChanged.emit(self._state)

    def _active_index(self) -> int:
        return next((idx for idx, tab in enumerate(self._state.tabs) if tab.tab_id == self._state.active_tab_id), 0)

    def _remember_file_path(self, action_key: str, path: Path) -> None:
        text_path = str(path)
        self._program_context = self._controller.remember_recent_file(
            self._program_context,
            path,
        )
        self._state = BinaryWorkbenchStateDTO(
            **{
                **state_payload(self._state),
                "directories": {**self._state.directories, action_key: str(path.parent)},
            }
        )
        self.programContextChanged.emit(self._program_context)
        self.stateChanged.emit(self._state)

    def _refresh_tab_label(self, tab_id: str, display_name: str) -> None:
        index = next((idx for idx, tab in enumerate(self._state.tabs) if tab.tab_id == tab_id), -1)
        if index < 0:
            return
        self.setTabText(index, tab_text(display_name))
        self.setTabToolTip(index, display_name)


def _internal_mapper(
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


def _is_transient_visible_context_update(
    previous: BinaryWorkbenchTabContextDTO,
    current: BinaryWorkbenchTabContextDTO,
) -> bool:
    if current.kind not in {BINARY_WORKBENCH_TAB_KIND.BINARY, BINARY_WORKBENCH_TAB_KIND.INTERNAL}:
        return False
    previous_values = dict(previous.__dict__)
    current_values = dict(current.__dict__)
    for field in TRANSIENT_VISIBLE_CONTEXT_FIELDS:
        previous_values.pop(field, None)
        current_values.pop(field, None)
    return previous_values == current_values
