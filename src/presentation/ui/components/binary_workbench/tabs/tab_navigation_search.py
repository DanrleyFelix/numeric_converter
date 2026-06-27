from src.core.binary_workbench.search_cache import SearchCacheQuery
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_DEFAULT_SEARCH_RESULT_LIMIT
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
        query_key = self._search_cache_query(mode, query, start_offset, end_offset, max_results)
        cached: list[int] = []
        missing_ranges = [(start_offset, end_offset)]
        search_cache = self._search_cache_for_find() if query_key is not None else None
        if search_cache is not None:
            cached = search_cache.cached_offsets(query_key)
            missing_ranges = search_cache.missing_ranges(query_key)
            if not missing_ranges:
                page.remember_search_end_offset(start_offset, end_offset)
                self._cache_search_results(mode, query, cached, start_offset, end_offset)
                return cached
        results = list(cached)
        for missing_start, missing_end in missing_ranges:
            remaining = None if max_results is None else max_results - len(results)
            if remaining is not None and remaining <= 0:
                break
            results.extend(page.find_offsets(mode, query, missing_start, missing_end, remaining))
        results = sorted(dict.fromkeys(results))
        if max_results is not None:
            results = results[:max_results]
        page.remember_search_end_offset(start_offset, end_offset)
        if search_cache is not None:
            search_cache.put(query_key, results)
            results = search_cache.cached_offsets(query_key)
        self._cache_search_results(mode, query, results, start_offset, end_offset)
        return results

    def last_search_end_offset(self) -> int | None:
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            return page.last_search_end_offset()
        return None

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
        compact_results = results[:BINARY_WORKBENCH_DEFAULT_SEARCH_RESULT_LIMIT]
        updated = BinaryWorkbenchTabContextDTO(
            **{
                **current.__dict__,
                "search_cache": {**current.search_cache, key: [f"0x{offset:08X}" for offset in compact_results]},
            }
        )
        self._replace_context(current.tab_id, updated)

    def _search_cache_query(
        self,
        mode: str,
        query: str,
        start_offset: int | None,
        end_offset: int | None,
        max_results: int | None,
    ) -> SearchCacheQuery | None:
        current = self.current_context()
        if current is None or not query or max_results is not None:
            return None
        source = current.source_path or current.workspace_path or current.tab_id
        source_id = f"{current.kind}:{source}:{current.file_size}:{current.active_version_name or ''}"
        return SearchCacheQuery(
            source_id=source_id,
            mode=mode,
            value=query.strip(),
            start_offset=start_offset,
            end_offset=end_offset,
            result_limit=max_results,
        )
