from pathlib import Path

from src.core.binary_workbench.version_overlays import (
    byte_overlays_from_instruction_overlays,
)
from src.core.binary_workbench.symbol_values import (
    effective_symbol_values,
    merged_symbol_values,
)
from src.core.binary_workbench.symbols.compatibility import (
    LegacySymbolsPayloadAdapter,
    definitions_payload,
)
from src.core.binary_workbench.symbols.definitions import SymbolScope
from src.core.binary_workbench.symbols.constants import MAX_SYMBOL_BATCH_SIZE
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_TAB_KIND
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
)
from src.presentation.repository.binary_workbench_workspace.constants import (
    GLOBAL_SYMBOLS,
)
from src.presentation.ui.components.binary_workbench.editor import BinaryWorkbenchEditorPage
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    labels_from_rows,
)
from src.presentation.ui.components.binary_workbench.editor.immediate_symbol_dialog import (
    ImmediateSymbolNameDialog,
)
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
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

    def global_symbols_library_path(self) -> str:
        """Return the one Global Symbols library selected for this session."""

        return self._global_symbols_path

    def set_global_symbols_library(self, path: Path) -> Path:
        """Canonicalize and link one Global Symbols file to every open tab."""

        canonical = self._workspace_repository.import_environment_file(
            GLOBAL_SYMBOLS,
            path,
        )
        self._workspace_repository.save_symbols_file(
            canonical,
            self._global_symbols,
        )
        self._global_symbols_path = str(canonical)
        tabs: list[BinaryWorkbenchTabContextDTO] = []
        program_context_changed = False
        for index, tab in enumerate(self._state.tabs):
            linked = self._workspace_repository.bind_global_symbols(tab, canonical)
            tabs.append(linked)
            page = self.widget(index)
            if isinstance(page, BinaryWorkbenchEditorPage):
                page.replace_workspace_metadata(linked)
            if linked.source_path and linked.workspace_path:
                updated_program_context = self._controller.remember_workspace(
                    self._program_context,
                    Path(linked.source_path),
                    Path(linked.workspace_path),
                )
                program_context_changed = (
                    program_context_changed
                    or updated_program_context != self._program_context
                )
                self._program_context = updated_program_context
        self._state = BinaryWorkbenchStateDTO(
            **{**state_payload(self._state), "tabs": tabs}
        )
        if program_context_changed:
            self.programContextChanged.emit(self._program_context)
        self.stateChanged.emit(self._state)
        return canonical

    def _restore_global_symbols_link(self) -> None:
        """Adopt only the first valid tab link without scanning Assembly rows."""

        self._global_symbols_path = ""
        for tab in self._state.tabs:
            value = tab.module_paths.get(GLOBAL_SYMBOLS, "")
            if not value or not Path(value).is_file():
                continue
            self._global_symbols_path = str(Path(value))
            break
        if not self._global_symbols_path:
            return
        self._global_symbols = merged_symbol_values(
            self._workspace_repository.load_symbols_file(
                Path(self._global_symbols_path)
            )
        )
        self._symbol_runtime.set_global_definitions(self._global_symbols)
        self._state = BinaryWorkbenchStateDTO(
            **{
                **state_payload(self._state),
                "global_symbols": dict(self._global_symbols),
                "global_symbol_definitions": tuple(
                    definitions_payload(self._symbol_runtime.globals.definitions())
                ),
            }
        )

    def _adopt_global_symbols_link(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> None:
        """Restore the first linked catalog and ignore later conflicting links."""

        value = context.module_paths.get(GLOBAL_SYMBOLS, "")
        if self._global_symbols_path or not value or not Path(value).is_file():
            return
        self._global_symbols_path = str(Path(value))
        self._global_symbols = merged_symbol_values(
            self._workspace_repository.load_symbols_file(Path(value))
        )
        self._symbol_runtime.set_global_definitions(self._global_symbols)
        self._state = BinaryWorkbenchStateDTO(
            **{
                **state_payload(self._state),
                "global_symbols": dict(self._global_symbols),
                "global_symbol_definitions": tuple(
                    definitions_payload(self._symbol_runtime.globals.definitions())
                ),
            }
        )

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
        apply_existing: bool = True,
    ) -> None:
        # Catalog loading must not invoke the complete Alt+S/F5 barrier.
        # current_context() flushes only already-delivered source changes.
        current = self.current_context()
        if current is None:
            return
        page = self.currentWidget()
        cursor_state = _editor_cursor_state(page)
        previous_symbols = _local_symbols(current)
        local_symbols = merged_symbol_values(variables, equates)
        definition_only = not apply_existing and _definition_only_addition(
            previous_symbols,
            local_symbols,
        )
        renamed = _single_symbol_rename(previous_symbols, local_symbols)
        changed_names = _changed_symbol_names(previous_symbols, local_symbols)
        bulk_catalog_change = (
            renamed is None and len(changed_names) > MAX_SYMBOL_BATCH_SIZE
        )
        changed_lines: tuple[int, ...] = ()
        if not bulk_catalog_change and not definition_only:
            self._ensure_symbol_runtime(current, page)
            changed_lines = self._symbol_runtime.lines_for_symbols(
                current.tab_id,
                changed_names,
            )
        self._symbol_runtime.set_local_definitions(current.tab_id, local_symbols)
        if definition_only:
            effective_symbols = effective_symbol_values(
                local_symbols,
                self._global_symbols,
            )
            current = BinaryWorkbenchTabContextDTO(
                **{
                    **current.__dict__,
                    "symbols": local_symbols,
                    "variables": effective_symbols,
                    "equates": effective_symbols,
                    "symbol_definitions": tuple(definitions_payload(
                        self._symbol_runtime.locals.for_tab(current.tab_id).definitions()
                    )),
                }
            )
            self._replace_context(current.tab_id, current)
            if isinstance(page, BinaryWorkbenchEditorPage):
                page.update_symbol_context(current)
                page.rederive_symbol_viewport(tuple(changed_names))
            _restore_editor_cursor(page, cursor_state)
            return
        if (
            isinstance(page, BinaryWorkbenchEditorPage)
            and page.grid._consistency_coordinator.supports_derived_updates()
        ):
            effective_symbols = effective_symbol_values(
                local_symbols,
                self._global_symbols,
            )
            current = BinaryWorkbenchTabContextDTO(
                **{
                    **current.__dict__,
                    "symbols": local_symbols,
                    "variables": effective_symbols,
                    "equates": effective_symbols,
                    "symbol_definitions": tuple(definitions_payload(
                        self._symbol_runtime.locals.for_tab(current.tab_id).definitions()
                    )),
                }
            )
            self._replace_context(current.tab_id, current)
            page.update_symbol_context(current)
            if renamed is not None:
                page.rename_symbol_tokens(*renamed, changed_lines)
            elif bulk_catalog_change:
                page.rederive_all_symbol_lines()
            else:
                page.rederive_symbol_lines(changed_lines)
            _restore_editor_cursor(page, cursor_state)
            return
        current = self._context_with_symbol_values(
            current,
            local_symbols,
            page,
        )
        self._set_current_context(current)
        _restore_editor_cursor(page, cursor_state)

    def set_global_symbols(
        self,
        symbols: dict[str, str],
        apply_existing: bool = True,
    ) -> None:
        # Flush current Qt edits without forcing a full synchronous rebuild.
        self.current_context()
        previous_globals = dict(self._global_symbols)
        self._global_symbols = merged_symbol_values(symbols)
        current_index = self.currentIndex()
        tabs = list(self._state.tabs)
        definition_only = not apply_existing and _definition_only_addition(
            previous_globals,
            self._global_symbols,
        )
        changed_lines: tuple[int, ...] = ()
        renamed = _single_symbol_rename(previous_globals, self._global_symbols)
        changed_names = _changed_symbol_names(
            previous_globals,
            self._global_symbols,
        )
        bulk_catalog_change = (
            renamed is None and len(changed_names) > MAX_SYMBOL_BATCH_SIZE
        )
        incremental_active = False
        if 0 <= current_index < len(tabs):
            active_page = self.widget(current_index)
            incremental_active = (
                isinstance(active_page, BinaryWorkbenchEditorPage)
                and active_page.grid._consistency_coordinator.supports_derived_updates()
            )
            if not definition_only and incremental_active and not bulk_catalog_change:
                self._ensure_symbol_runtime(tabs[current_index], active_page)
                changed_lines = self._symbol_runtime.lines_for_symbols(
                    tabs[current_index].tab_id,
                    changed_names,
                )
        self._symbol_runtime.set_global_definitions(self._global_symbols)
        if previous_globals == self._global_symbols:
            return
        if 0 <= current_index < len(tabs):
            if definition_only:
                current = tabs[current_index]
                local_symbols = _local_symbols(current)
                effective_symbols = effective_symbol_values(
                    local_symbols,
                    self._global_symbols,
                )
                tabs[current_index] = BinaryWorkbenchTabContextDTO(
                    **{
                        **current.__dict__,
                        "variables": effective_symbols,
                        "equates": effective_symbols,
                    }
                )
            elif incremental_active:
                current = tabs[current_index]
                effective_symbols = effective_symbol_values(
                    _local_symbols(current),
                    self._global_symbols,
                )
                tabs[current_index] = BinaryWorkbenchTabContextDTO(
                    **{
                        **current.__dict__,
                        "variables": effective_symbols,
                        "equates": effective_symbols,
                    }
                )
            else:
                tabs[current_index] = self._materialize_symbol_context(
                    tabs[current_index],
                    self.widget(current_index),
                )
        if not definition_only:
            self._pending_global_symbol_tabs.update(
                tab.tab_id for index, tab in enumerate(tabs) if index != current_index
            )
        self._state = BinaryWorkbenchStateDTO(
            **{
                **state_payload(self._state),
                "tabs": tabs,
                "global_symbols": dict(self._global_symbols),
                "global_symbol_definitions": tuple(definitions_payload(
                    self._symbol_runtime.globals.definitions()
                )),
            }
        )
        if 0 <= self.currentIndex() < len(tabs):
            active = tabs[self.currentIndex()]
            self._replace_context_without_emit(active.tab_id, active)
            tabs = self._state.tabs
        if 0 <= current_index < len(tabs):
            page = self.widget(current_index)
            if isinstance(page, BinaryWorkbenchEditorPage):
                if definition_only:
                    page.update_symbol_context(tabs[current_index])
                    page.rederive_symbol_viewport(tuple(changed_names))
                elif incremental_active:
                    page.update_symbol_context(tabs[current_index])
                    if renamed is not None:
                        page.rename_symbol_tokens(*renamed, changed_lines)
                    elif bulk_catalog_change:
                        page.rederive_all_symbol_lines()
                    else:
                        page.rederive_symbol_lines(changed_lines)
                else:
                    page.load_context(tabs[current_index])
                self._stale_context_pages.discard(tabs[current_index].tab_id)
        self.stateChanged.emit(self._state)

    def _context_with_global_symbols(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> BinaryWorkbenchTabContextDTO:
        self._adopt_global_symbols_link(context)
        # A lazy Local Symbols payload must not hide the already loaded Global
        # catalog.  Publishing the shared lookup map is cheap and does not
        # materialize, scan or assemble the inactive tab.
        local_symbols = _local_symbols(context)
        effective_symbols = effective_symbol_values(
            local_symbols,
            self._global_symbols,
        )
        module_paths = dict(context.module_paths)
        if self._global_symbols_path and GLOBAL_SYMBOLS not in module_paths:
            module_paths[GLOBAL_SYMBOLS] = self._global_symbols_path
        return BinaryWorkbenchTabContextDTO(
            **{
                **context.__dict__,
                "symbols": local_symbols,
                "variables": effective_symbols,
                "equates": effective_symbols,
                "module_paths": module_paths,
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
            "symbol_offsets": {name: [offset] for name, offset in labels.items()},
            "symbol_definitions": tuple(definitions_payload(
                self._symbol_runtime.locals.for_tab(current.tab_id).definitions()
            )),
            "symbol_migration_pending": False,
            "lazy_symbol_payload": {},
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

    def _materialize_symbol_context(
        self,
        context: BinaryWorkbenchTabContextDTO,
        page: object,
    ) -> BinaryWorkbenchTabContextDTO:
        """Convert and index Symbols only when their owning tab is activated."""

        if context.lazy_symbol_payload:
            adapted = LegacySymbolsPayloadAdapter(self._state.workspace_id).adapt(
                context.lazy_symbol_payload,
                SymbolScope.LOCAL,
                context.tab_id,
            )
            local_symbols = {item.name: item.value for item in adapted.definitions}
            conflicts = list(context.symbol_migration_conflicts)
            for raw_version in context.lazy_symbol_payload.get(
                "version_symbol_payloads",
                (),
            ):
                if not isinstance(raw_version, dict):
                    continue
                version_adapted = LegacySymbolsPayloadAdapter(
                    self._state.workspace_id
                ).adapt(raw_version, SymbolScope.LOCAL, context.tab_id)
                version_symbols = {
                    item.name: item.value for item in version_adapted.definitions
                }
                if not local_symbols:
                    local_symbols = version_symbols
                elif version_symbols and version_symbols != local_symbols:
                    conflicts.append(
                        f"Version '{raw_version.get('name', '')}' contains conflicting Local Symbols."
                    )
            definitions = tuple(
                LegacySymbolsPayloadAdapter(self._state.workspace_id).from_mapping(
                    local_symbols,
                    SymbolScope.LOCAL,
                    context.tab_id,
                )
            )
            context = BinaryWorkbenchTabContextDTO(
                **{
                    **context.__dict__,
                    "symbols": local_symbols,
                    "symbol_definitions": tuple(definitions_payload(definitions)),
                    "lazy_symbol_payload": {},
                    "symbol_migration_pending": False,
                    "symbol_migration_conflicts": tuple(conflicts),
                }
            )
        else:
            local_symbols = _local_symbols(context)
        needs_globals = context.tab_id in self._pending_global_symbol_tabs
        if needs_globals or context.variables != effective_symbol_values(
            local_symbols, self._global_symbols
        ):
            context = self._context_with_symbol_values(context, local_symbols, page)
        if not self._symbol_runtime.is_materialized(context.tab_id):
            base = _first_file_offset(context)
            source_rows = _runtime_source_rows(context, page)
            self._symbol_runtime.materialize_tab(
                context.tab_id,
                source_rows,
                local_symbols,
                base,
                _visible_symbol_range(page, len(source_rows)),
            )
        self._pending_global_symbol_tabs.discard(context.tab_id)
        return context

    def symbol_offsets_for(self, tab_id: str, name: str) -> list[str]:
        """Query one indexed Symbol without rebuilding a global offset map."""

        context = next((tab for tab in self._state.tabs if tab.tab_id == tab_id), None)
        if context is None:
            return []
        if not self._symbol_runtime.is_materialized(tab_id):
            context = self._materialize_symbol_context(context, self.currentWidget())
            self._replace_context_without_emit(tab_id, context)
        return self._symbol_runtime.offsets_for(tab_id, name)

    def _ensure_symbol_runtime(
        self,
        context: BinaryWorkbenchTabContextDTO,
        page: object,
    ) -> None:
        """Materialize indices only for the active tab and current source rows."""

        if self._symbol_runtime.is_materialized(context.tab_id):
            return
        source_rows = _runtime_source_rows(context, page)
        self._symbol_runtime.materialize_tab(
            context.tab_id,
            source_rows,
            _local_symbols(context),
            _first_file_offset(context),
            _visible_symbol_range(page, len(source_rows)),
        )

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


def _definition_only_addition(
    previous: dict[str, str],
    current: dict[str, str],
) -> bool:
    """Detect additions that cannot affect any already-resolved occurrence."""

    old = {name.casefold(): value for name, value in previous.items()}
    new = {name.casefold(): value for name, value in current.items()}
    return (
        new != old
        and len(new) >= len(old)
        and all(new.get(name) == value for name, value in old.items())
    )


def _changed_symbol_names(
    previous: dict[str, str],
    current: dict[str, str],
) -> set[str]:
    """Return normalized names whose definition was added, changed, or removed."""

    old = {name.casefold(): value for name, value in previous.items()}
    new = {name.casefold(): value for name, value in current.items()}
    return {
        name
        for name in old.keys() | new.keys()
        if old.get(name) != new.get(name)
    }


def _single_symbol_rename(
    previous: dict[str, str],
    current: dict[str, str],
) -> tuple[str, str] | None:
    """Recognize the rename shape exposed by the legacy mapping API."""

    old = {name.casefold(): name for name in previous}
    new = {name.casefold(): name for name in current}
    removed = [name for key, name in old.items() if key not in new]
    added = [name for key, name in new.items() if key not in old]
    return (removed[0], added[0]) if len(removed) == 1 and len(added) == 1 else None


def _first_file_offset(context: BinaryWorkbenchTabContextDTO) -> int:
    for row in context.rows:
        raw = row.offsets.get("File", "-")
        if raw != "-":
            try:
                return int(raw, 0)
            except ValueError:
                continue
    return 0


def _runtime_source_rows(
    context: BinaryWorkbenchTabContextDTO,
    page: object,
) -> list:
    """Prefer the active editor source over a deferred context snapshot.

    Opening Assembly text can precede the debounced rowsChanged commit. Symbol
    loading must index those visible authoritative rows, not the older blank
    DTO kept by the tab while that lightweight notification is pending.
    """

    if isinstance(page, BinaryWorkbenchEditorPage) and not page.grid._virtual:
        rows = page.grid.export_rows()
        if rows:
            return rows
    return list(context.rows)


def _visible_symbol_range(page: object, row_count: int) -> tuple[int, int] | None:
    if not isinstance(page, BinaryWorkbenchEditorPage) or row_count <= 0:
        return None
    editor = page.grid.instructions
    first = max(0, editor.firstVisibleBlock().blockNumber())
    height = max(1, editor.fontMetrics().height())
    visible = max(1, editor.viewport().height() // height + 2)
    return first, min(row_count - 1, first + visible + 64)


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
    set_cursor_position(cursor, block.position() + min(column, len(block.text())))
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
