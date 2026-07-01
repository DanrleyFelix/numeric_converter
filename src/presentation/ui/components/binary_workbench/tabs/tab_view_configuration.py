from dataclasses import replace

from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchEncodingTableDTO,
    BinaryWorkbenchOffsetRegionDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchViewPreferencesDTO,
)
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_TAB_KIND
from pathlib import Path

from src.presentation.repository.binary_workbench_workspace.constants import OFFSET_REGIONS
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor import BinaryWorkbenchEditorPage
from src.presentation.ui.components.binary_workbench.tabs.tab_state_payload import (
    state_payload,
)


class TabViewConfigurationMixin:
    def decoded_tables_directory(self) -> str:
        return str(self._workspace_repository.decoded_tables_directory)

    def set_current_visible_columns(self, visible_columns: dict[str, bool]) -> None:
        current = self.current_context()
        if current is None:
            return
        preferences = BinaryWorkbenchViewPreferencesDTO(
            visible_columns={
                **current.view_preferences.visible_columns,
                **visible_columns,
                BINARY_WORKBENCH_TEXT.INSTRUCTION: True,
            },
            decoded_text_tables=list(current.view_preferences.decoded_text_tables),
        )
        self._set_view_preferences_for_related_tabs(current, preferences)

    def set_current_encoding_tables(
        self,
        tables: list[BinaryWorkbenchEncodingTableDTO],
        enabled_names: list[str],
    ) -> None:
        current = self.current_context()
        if current is None:
            return
        preferences = BinaryWorkbenchViewPreferencesDTO(
            visible_columns=dict(current.view_preferences.visible_columns),
            decoded_text_tables=list(enabled_names),
        )
        self._state = BinaryWorkbenchStateDTO(
            **{
                **state_payload(self._state),
                "encoding_tables": list(tables),
                "tabs": [
                    replace(tab, encoding_tables=list(tables))
                    for tab in self._state.tabs
                ],
            }
        )
        self._set_current_context(replace(
            current,
            encoding_tables=list(tables),
            view_preferences=preferences,
        ))
        self._set_view_preferences_for_related_tabs(current, preferences)
        self._refresh_encoding_table_pages(list(tables))


    def _set_view_preferences_for_related_tabs(
        self,
        current: BinaryWorkbenchTabContextDTO,
        preferences: BinaryWorkbenchViewPreferencesDTO,
    ) -> None:
        parent_id = current.tab_id
        if current.kind == BINARY_WORKBENCH_TAB_KIND.INTERNAL:
            parent = self._internal_parent_context(current)
            parent_id = parent.tab_id if parent is not None else current.internal_parent_tab_id or current.tab_id
        tabs = []
        for tab in self._state.tabs:
            if tab.tab_id == parent_id:
                tabs.append(replace(tab, view_preferences=preferences))
                continue
            if _is_related_internal_tab(tab, parent_id, current.source_path):
                tabs.append(replace(tab, view_preferences=_internal_view_preferences(preferences)))
                continue
            tabs.append(tab)
        self._state = BinaryWorkbenchStateDTO(**{**state_payload(self._state), "tabs": tabs})
        index = self.currentIndex()
        if 0 <= index < len(tabs):
            self._set_current_context(tabs[index])
        else:
            self.stateChanged.emit(self._state)
    def set_current_offset_regions(
        self,
        regions: list[BinaryWorkbenchOffsetRegionDTO],
    ) -> None:
        current = self.current_context()
        if current is None:
            return
        self._set_current_context(BinaryWorkbenchTabContextDTO(
            **{**current.__dict__, "offset_regions": list(regions), "offset_regions_loaded": True}
        ))

    def offset_regions_for_current_context(self) -> list[BinaryWorkbenchOffsetRegionDTO]:
        current = self.current_context()
        if current is None:
            return []
        path = current.module_paths.get(OFFSET_REGIONS)
        if path:
            return self._workspace_repository.load_offset_regions_file(Path(path))
        return list(current.offset_regions)

    def offset_region_details_for_current_context(self, name: str, offset: int) -> str:
        current = self.current_context()
        if current is None:
            return ""
        path = current.module_paths.get(OFFSET_REGIONS)
        if not path:
            return ""
        return self._workspace_repository.load_offset_region_details(Path(path), name, offset)

    def _context_with_universal_encoding_tables(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> BinaryWorkbenchTabContextDTO:
        if not self._state.encoding_tables:
            return context
        return replace(context, encoding_tables=list(self._state.encoding_tables))

    def _refresh_encoding_table_pages(
        self,
        tables: list[BinaryWorkbenchEncodingTableDTO],
    ) -> None:
        for index, context in enumerate(self._state.tabs):
            updated = replace(context, encoding_tables=list(tables))
            page = self.widget(index)
            if isinstance(page, BinaryWorkbenchEditorPage):
                page.replace_context(updated)
                if index == self.currentIndex():
                    page.load_context(updated)


def _is_related_internal_tab(
    tab: BinaryWorkbenchTabContextDTO,
    parent_id: str,
    source_path: str | None,
) -> bool:
    return (
        tab.kind == BINARY_WORKBENCH_TAB_KIND.INTERNAL
        and (
            tab.internal_parent_tab_id == parent_id
            or bool(source_path and tab.source_path == source_path)
        )
    )


def _internal_view_preferences(
    preferences: BinaryWorkbenchViewPreferencesDTO,
) -> BinaryWorkbenchViewPreferencesDTO:
    return BinaryWorkbenchViewPreferencesDTO(
        visible_columns={
            name: visible
            for name, visible in preferences.visible_columns.items()
            if name != "Binary"
        },
        decoded_text_tables=list(preferences.decoded_text_tables),
    )
