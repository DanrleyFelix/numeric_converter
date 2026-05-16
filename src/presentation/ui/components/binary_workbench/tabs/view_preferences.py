from copy import deepcopy

from src.modules.dtos import BinaryWorkbenchStateDTO, BinaryWorkbenchViewPreferencesDTO


def seed_view_preferences(
    state: BinaryWorkbenchStateDTO,
    preferred: BinaryWorkbenchViewPreferencesDTO | None = None,
) -> BinaryWorkbenchViewPreferencesDTO:
    if preferred is not None:
        return copy_view_preferences(preferred)
    if not state.share_view_preferences or not state.tabs:
        return BinaryWorkbenchViewPreferencesDTO()
    active = next((tab for tab in state.tabs if tab.tab_id == state.active_tab_id), None)
    return copy_view_preferences(active.view_preferences) if active else BinaryWorkbenchViewPreferencesDTO()


def copy_view_preferences(
    value: BinaryWorkbenchViewPreferencesDTO,
) -> BinaryWorkbenchViewPreferencesDTO:
    return BinaryWorkbenchViewPreferencesDTO(
        visible_columns=deepcopy(value.visible_columns),
        decoded_text_tables=list(value.decoded_text_tables),
    )
