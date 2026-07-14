from src.core.binary_workbench.version_overlays import (
    byte_overlays_from_instruction_overlays,
)
from src.core.binary_workbench.symbol_values import (
    effective_symbol_values,
    merged_symbol_values,
)
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_TAB_KIND
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
)
from src.presentation.ui.components.binary_workbench.editor import BinaryWorkbenchEditorPage
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    labels_from_rows,
)
from src.presentation.ui.components.binary_workbench.editor.immediate_symbol_dialog import (
    ImmediateSymbolNameDialog,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.symbols import symbol_offsets
from src.presentation.ui.components.binary_workbench.tabs.tab_state_payload import (
    lba_sector_size,
    state_payload,
)
from src.presentation.ui.components.binary_workbench.tabs.tab_workspace import (
    _rows_with_loaded_symbols,
)


class TabLibrariesMixin:
    def set_current_internal_files(
        self,
        internal_files: list[BinaryWorkbenchInternalFileDTO],
        lba_sector_size_value: int | None = None,
    ) -> None:
        current = self.current_context()
        if current is None:
            return
        updates: dict[str, object] = {"internal_files": internal_files}
        if lba_sector_size_value is not None:
            updates["lba_sector_size"] = lba_sector_size(lba_sector_size_value)
        self._set_current_context(BinaryWorkbenchTabContextDTO(**{**current.__dict__, **updates}))

    def save_current_lba_filesystem(self, name: str) -> None:
        return

    def load_current_lba_filesystem(self, name: str) -> bool:
        return False

    def local_symbols(
        self,
        context: BinaryWorkbenchTabContextDTO | None = None,
    ) -> dict[str, str]:
        current = context or self.current_context()
        return _local_symbols(current) if current is not None else {}

    def global_symbols(self) -> dict[str, str]:
        return dict(self._global_symbols)

    def _edit_symbol_from_editor(self, name: str) -> None:
        current = self.current_context()
        if current is None:
            return
        local_symbols = self.local_symbols(current)
        local_name = _matching_symbol_name(local_symbols, name)
        global_name = _matching_symbol_name(self._global_symbols, name)
        source = local_symbols if local_name is not None else self._global_symbols
        source_name = local_name or global_name
        if source_name is None:
            return
        dialog = ImmediateSymbolNameDialog(
            BINARY_WORKBENCH_TEXT.CHANGE_SYMBOL_VALUES,
            source[source_name],
            self,
            name=source_name,
            editable_value=True,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        updated_name = dialog.symbol_name().strip().lstrip("_@")
        updated_value = dialog.symbol_value().strip()
        if not updated_name or not updated_value:
            return
        updated = dict(source)
        updated.pop(source_name, None)
        updated[updated_name] = updated_value
        if local_name is not None:
            self.set_current_symbols(updated, {}, current.labels)
        else:
            self.set_global_symbols(updated)

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
        cursor_state = _editor_cursor_state(page)
        local_symbols = merged_symbol_values(variables, equates)
        current = self._context_with_symbol_values(
            current,
            local_symbols,
            page,
        )
        self._set_current_context(current)
        _restore_editor_cursor(page, cursor_state)

    def set_global_symbols(self, symbols: dict[str, str]) -> None:
        self.commit_current_editor_text()
        self._global_symbols = merged_symbol_values(symbols)
        tabs = [
            self._context_with_symbol_values(
                context,
                _local_symbols(context),
                self.widget(index),
            )
            for index, context in enumerate(self._state.tabs)
        ]
        self._state = BinaryWorkbenchStateDTO(
            **{**state_payload(self._state), "tabs": tabs}
        )
        if 0 <= self.currentIndex() < len(tabs):
            active = tabs[self.currentIndex()]
            self._replace_context_without_emit(active.tab_id, active)
            tabs = self._state.tabs
        for index, context in enumerate(tabs):
            page = self.widget(index)
            if not isinstance(page, BinaryWorkbenchEditorPage):
                continue
            if page is self.currentWidget():
                page.load_context(context)
                self._stale_context_pages.discard(context.tab_id)
            else:
                self._stale_context_pages.add(context.tab_id)
        self.stateChanged.emit(self._state)

    def _context_with_global_symbols(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> BinaryWorkbenchTabContextDTO:
        local_symbols = _local_symbols(context)
        effective_symbols = effective_symbol_values(
            local_symbols,
            self._global_symbols,
        )
        return BinaryWorkbenchTabContextDTO(
            **{
                **context.__dict__,
                "symbols": local_symbols,
                "variables": effective_symbols,
                "equates": effective_symbols,
            }
        )

    def _context_with_symbol_values(
        self,
        current: BinaryWorkbenchTabContextDTO,
        local_symbols: dict[str, str],
        page: object,
    ) -> BinaryWorkbenchTabContextDTO:
        effective_symbols = effective_symbol_values(
            local_symbols,
            self._global_symbols,
        )
        labels = labels_from_rows(current.rows)
        if isinstance(page, BinaryWorkbenchEditorPage) and page is self.currentWidget():
            rows = page.grid.rows_encoded_with_symbols(
                effective_symbols,
                effective_symbols,
                labels,
            )
        else:
            rows = _rows_with_loaded_symbols(
                BinaryWorkbenchTabContextDTO(
                    **{
                        **current.__dict__,
                        "variables": effective_symbols,
                        "equates": effective_symbols,
                    }
                )
            )
        labels = labels_from_rows(rows)
        updates: dict[str, object] = {
            "symbols": local_symbols,
            "variables": effective_symbols,
            "equates": effective_symbols,
            "labels": labels,
            "rows": rows,
            "symbol_offsets": symbol_offsets(
                rows,
                effective_symbols,
                effective_symbols,
                labels,
            ),
        }
        if current.kind in {
            BINARY_WORKBENCH_TAB_KIND.BINARY,
            BINARY_WORKBENCH_TAB_KIND.INTERNAL,
        }:
            updates["byte_overlays"] = _byte_overlays_with_symbols(
                current,
                effective_symbols,
                effective_symbols,
            )
            updates["version_dirty"] = True
        return BinaryWorkbenchTabContextDTO(**{**current.__dict__, **updates})

    def save_current_symbols(self, name: str) -> None:
        return

    def load_current_symbols(self, name: str) -> bool:
        return False


def _local_symbols(
    context: BinaryWorkbenchTabContextDTO,
) -> dict[str, str]:
    return merged_symbol_values(context.symbols)


def _matching_symbol_name(symbols: dict[str, str], name: str) -> str | None:
    target = name.strip().lstrip("_@").casefold()
    return next((item for item in symbols if item.casefold() == target), None)


def _editor_cursor_state(page: object) -> tuple[str, int, int] | None:
    if not isinstance(page, BinaryWorkbenchEditorPage):
        return None
    kind = page.grid.focused_editor_kind()
    editor = _editor_for_kind(page, kind)
    if editor is None:
        return None
    cursor = editor.textCursor()
    return kind, cursor.blockNumber(), cursor.positionInBlock()


def _restore_editor_cursor(
    page: object,
    state: tuple[str, int, int] | None,
) -> None:
    if not isinstance(page, BinaryWorkbenchEditorPage) or state is None:
        return
    kind, block_number, column = state
    editor = _editor_for_kind(page, kind)
    if editor is None:
        return
    block = editor.document().findBlockByNumber(block_number)
    if not block.isValid():
        return
    cursor = editor.textCursor()
    cursor.setPosition(block.position() + min(column, len(block.text())))
    editor.setTextCursor(cursor)
    editor.setFocus()


def _editor_for_kind(page: BinaryWorkbenchEditorPage, kind: str | None):
    return {
        BINARY_WORKBENCH_TEXT.BYTES: page.grid.bytes,
        BINARY_WORKBENCH_TEXT.INSTRUCTION: page.grid.instructions,
        BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS: page.grid.raw_instructions,
    }.get(kind)


def _byte_overlays_with_symbols(
    current: BinaryWorkbenchTabContextDTO,
    variables: dict[str, str],
    equates: dict[str, str],
) -> dict[str, str]:
    instruction_offsets = set(current.instruction_overlays)
    byte_overlays = {
        offset: value
        for offset, value in current.byte_overlays.items()
        if offset not in instruction_offsets
    }
    byte_overlays.update(
        byte_overlays_from_instruction_overlays(
            current.instruction_overlays,
            variables,
            equates,
        )
    )
    return byte_overlays
