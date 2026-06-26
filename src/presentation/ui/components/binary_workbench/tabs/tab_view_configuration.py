from dataclasses import replace

from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchEncodingTableDTO,
    BinaryWorkbenchOffsetRegionDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchViewPreferencesDTO,
)
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
        self._set_current_context(BinaryWorkbenchTabContextDTO(
            **{**current.__dict__, "view_preferences": preferences}
        ))

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
        self._refresh_encoding_table_pages(list(tables))

    def set_current_offset_regions(
        self,
        regions: list[BinaryWorkbenchOffsetRegionDTO],
    ) -> None:
        current = self.current_context()
        if current is None:
            return
        self._set_current_context(BinaryWorkbenchTabContextDTO(
            **{**current.__dict__, "offset_regions": list(regions)}
        ))

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
