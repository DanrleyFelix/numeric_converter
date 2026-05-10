from src.modules.dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.editor import BinaryWorkbenchEditorPage


class TabNavigationSearchMixin:
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

    def _cache_search_results(self, mode: str, query: str, results: list[int]) -> None:
        current = self.current_context()
        if current is None or not query:
            return
        key = f"{mode}:{query}"
        updated = BinaryWorkbenchTabContextDTO(
            **{
                **current.__dict__,
                "search_cache": {**current.search_cache, key: [f"0x{offset:08X}" for offset in results]},
            }
        )
        self._replace_context(current.tab_id, updated)
