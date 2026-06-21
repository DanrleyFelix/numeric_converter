from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.editor import BinaryWorkbenchEditorPage


class TabNavigationSearchMixin:
    def commit_current_editor_text(self) -> None:
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.commit_current_editor_text()

    def go_to_offset(self, offset: int) -> None:
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.go_to_offset(offset)

    def go_to_instruction_offset(self, offset: int) -> None:
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.go_to_instruction_offset(offset)

    def select_block(self, start_offset: int, end_offset: int) -> None:
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.select_block(start_offset, end_offset)

    def select_all_content(self) -> None:
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.select_all_content()

    def find_text(
        self,
        mode: str,
        query: str,
        start_offset: int | None = None,
        end_offset: int | None = None,
        max_results: int | None = None,
    ) -> bool:
        results = self.find_offsets(mode, query, start_offset, end_offset, max_results)
        page = self.currentWidget()
        if results and isinstance(page, BinaryWorkbenchEditorPage):
            page.go_to_offset(results[0])
        return bool(results)

    def find_offsets(
        self,
        mode: str,
        query: str,
        start_offset: int | None = None,
        end_offset: int | None = None,
        max_results: int | None = None,
    ) -> list[int]:
        page = self.currentWidget()
        if not isinstance(page, BinaryWorkbenchEditorPage):
            return []
        results = page.find_offsets(mode, query, start_offset, end_offset, max_results)
        self._cache_search_results(mode, query, results, start_offset, end_offset)
        return results

    def focused_editor_kind(self) -> str | None:
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            return page.focused_editor_kind()
        return None

    def _cache_search_results(
        self,
        mode: str,
        query: str,
        results: list[int],
        start_offset: int | None = None,
        end_offset: int | None = None,
    ) -> None:
        current = self.current_context()
        if current is None or not query:
            return
        key = f"{mode}:{query}:{start_offset or ''}:{end_offset or ''}"
        if start_offset is None and end_offset is None:
            key = f"{mode}:{query}"
        updated = BinaryWorkbenchTabContextDTO(
            **{
                **current.__dict__,
                "search_cache": {**current.search_cache, key: [f"0x{offset:08X}" for offset in results]},
            }
        )
        self._replace_context(current.tab_id, updated)
