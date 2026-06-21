from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchEncodingTableDTO,
    BinaryWorkbenchOffsetRegionDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchViewPreferencesDTO,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT


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
        self._set_current_context(BinaryWorkbenchTabContextDTO(
            **{
                **current.__dict__,
                "encoding_tables": list(tables),
                "view_preferences": preferences,
            }
        ))

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
