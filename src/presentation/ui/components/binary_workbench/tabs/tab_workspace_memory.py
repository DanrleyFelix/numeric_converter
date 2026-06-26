from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_DEFAULT_VERSION_NAME,
    BINARY_WORKBENCH_TAB_KIND,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.editor import (
    BinaryWorkbenchEditorPage,
)
from src.presentation.ui.components.binary_workbench.tabs.workspace_memory import (
    WORKSPACE_HEAVY_TAB_LIMIT,
    unload_workspace_heavy_context,
    unloadable_workspace_context,
    workspace_heavy_context_loaded,
    workspace_heavy_context_unloaded,
)


class TabWorkspaceMemoryMixin:
    def _initialize_workspace_memory(self) -> None:
        self._workspace_access_counter = 0
        self._workspace_tab_access: dict[str, int] = {}

    def _remember_workspace_tab_access(self, tab_id: str) -> None:
        self._workspace_access_counter += 1
        self._workspace_tab_access[tab_id] = self._workspace_access_counter

    def _forget_workspace_tab_access(self, tab_id: str) -> None:
        self._workspace_tab_access.pop(tab_id, None)

    def _ensure_workspace_heavy_loaded(self, index: int) -> None:
        context = self.context_at(index)
        if context is None:
            return
        if workspace_heavy_context_unloaded(context):
            loaded = self._workspace_context_for_page(context)
            if loaded is not context:
                self._replace_context_without_emit(context.tab_id, loaded)
                page = self.widget(index)
                if isinstance(page, BinaryWorkbenchEditorPage):
                    page.load_context(loaded)
                context = loaded
        if workspace_heavy_context_loaded(context):
            self._remember_workspace_tab_access(context.tab_id)

    def _workspace_context_for_page(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> BinaryWorkbenchTabContextDTO:
        if not workspace_heavy_context_unloaded(context):
            return context
        path = Path(context.workspace_path or "")
        if not path.exists():
            return context
        return self._with_symbol_offsets(
            self._workspace_repository.load_tab_workspace(context, path)
        )

    def _enforce_workspace_heavy_limit(self) -> None:
        while len(self._loaded_workspace_heavy_tabs()) > WORKSPACE_HEAVY_TAB_LIMIT:
            index = self._least_accessed_workspace_heavy_tab()
            if index is None or not self._unload_workspace_heavy_tab(index):
                return

    def _loaded_workspace_heavy_tabs(self) -> list[str]:
        return [
            tab.tab_id
            for tab in self._state.tabs
            if workspace_heavy_context_loaded(tab)
            and unloadable_workspace_context(tab)
        ]

    def _least_accessed_workspace_heavy_tab(self) -> int | None:
        current = self.currentIndex()
        candidates = [
            (index, self._workspace_tab_access.get(tab.tab_id, 0))
            for index, tab in enumerate(self._state.tabs)
            if index != current
            and workspace_heavy_context_loaded(tab)
            and unloadable_workspace_context(tab)
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda item: item[1])[0]

    def _unload_workspace_heavy_tab(self, index: int) -> bool:
        context = self.context_at(index)
        if context is None:
            return False
        persisted = self._persist_workspace_context_for_unload(index, context)
        if persisted is None:
            return False
        unloaded = unload_workspace_heavy_context(persisted)
        self._replace_context_without_emit(unloaded.tab_id, unloaded)
        page = self.widget(index)
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.release_heavy_resources(unloaded)
        return True

    def _persist_workspace_context_for_unload(
        self,
        index: int,
        context: BinaryWorkbenchTabContextDTO,
    ) -> BinaryWorkbenchTabContextDTO | None:
        page = self.widget(index)
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.commit_current_editor_text()
            context = page.current_context()
            self._replace_context_without_emit(context.tab_id, context)
        if context.kind == BINARY_WORKBENCH_TAB_KIND.INTERNAL:
            return self._persist_internal_workspace_context(context)
        if context.kind == BINARY_WORKBENCH_TAB_KIND.BINARY:
            context = self._context_with_current_version(context)
        saved = self._workspace_repository.save_tab_workspace(context)
        self._remember_workspace_for_source(saved)
        return self._with_symbol_offsets(saved)

    def _persist_internal_workspace_context(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> BinaryWorkbenchTabContextDTO | None:
        if not self._save_internal_parent_workspace(context, None):
            return None
        return next(
            (
                tab
                for tab in self._state.tabs
                if tab.tab_id == context.tab_id
            ),
            None,
        )

    def _context_with_current_version(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> BinaryWorkbenchTabContextDTO:
        name = context.active_version_name or BINARY_WORKBENCH_DEFAULT_VERSION_NAME
        version = self._version_from_current(name, context)
        return replace(
            context,
            versions=[item for item in context.versions if item.name != name]
            + [version],
            active_version_name=name,
            version_dirty=True,
        )
