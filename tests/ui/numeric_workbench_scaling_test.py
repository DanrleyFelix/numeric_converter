import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QItemSelectionModel, QObject
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QWidget

from src.core.command_window.completion import PrefixCatalog
from src.main import create_main_window
from src.modules.application_dtos import ApplicationContextDTO
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchPreferencesDTO,
    BinaryWorkbenchStateDTO,
)
from src.modules.services import (
    BinaryWorkbenchPreferencesService,
    WorkspaceStateService,
)
from src.presentation.ui.components.command_panel.completion import PagedCompletionModel
from src.presentation.ui.components.workspace_table import WorkspaceRow, WorkspaceTableDialog
from src.presentation.ui.components.workspace_table.constants import (
    WORKSPACE_TABLE_SIZE,
    WORKSPACE_TABLE_SPACING,
)
from src.presentation.ui.main_window.autosave import NumericAutosaveScheduler


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_numeric_typing_arms_one_timer_without_binary_persistence():
    _app()
    window = create_main_window(Path(tempfile.mkdtemp()))
    binary_saves: list[object] = []
    window._state_service.save_default_binary_context = binary_saves.append

    QTest.keyClicks(window.body.command_panel.editor, "12345")

    assert binary_saves == []
    assert window._numeric_autosave._pending is True
    assert window._numeric_autosave._timer.isActive()


def test_closed_binary_repositories_are_loaded_only_on_explicit_open(monkeypatch):
    _app()
    calls: list[str] = []
    monkeypatch.setattr(
        WorkspaceStateService,
        "load_default_binary_context",
        lambda _self: calls.append("state") or BinaryWorkbenchStateDTO(),
    )
    monkeypatch.setattr(
        BinaryWorkbenchPreferencesService,
        "load",
        lambda _self: calls.append("preferences")
        or BinaryWorkbenchPreferencesDTO(),
    )
    window = create_main_window(Path(tempfile.mkdtemp()))

    QTest.keyClicks(window.body.command_panel.editor, "12345")
    assert calls == []

    window._open_binary_workbench()
    assert calls == ["state", "preferences"]
    window._binary_workbench_window.close()
    window._numeric_autosave.shutdown()


def test_numeric_open_action_calls_native_dialog_directly(monkeypatch):
    """Keep native pickers on the direct QAction path without queued lag."""

    _app()
    window = create_main_window(Path(tempfile.mkdtemp()))
    calls = []
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args: (calls.append(args) or ("", "")),
    )

    window.toolbar.load_workspace_action.trigger()
    assert len(calls) == 1
    window._numeric_autosave.shutdown()


def test_locked_binary_autosave_does_not_replace_numeric_feedback():
    _app()
    window = create_main_window(Path(tempfile.mkdtemp()))
    window.footer.set_status("Numeric feedback")

    def reject_save(_state):
        raise PermissionError("locked")

    window._state_service.save_default_binary_context = reject_save
    window._persist_binary_state()

    assert window.footer.status.text() == "Numeric feedback"
    assert not hasattr(window, "_binary_state_persistence")
    window._numeric_autosave.shutdown()


def test_binary_state_signal_reuses_exported_state_without_recollecting(monkeypatch):
    """Opening/importing Binary state must not flush the editor a second time."""

    _app()
    window = create_main_window(Path(tempfile.mkdtemp()))
    state = BinaryWorkbenchStateDTO(active_tab_id="opened")
    monkeypatch.setattr(
        window,
        "_collect_binary_workbench_state",
        lambda: (_ for _ in ()).throw(AssertionError("unexpected Binary export")),
    )
    window._remember_binary_workbench_state(state)

    assert window._binary_workbench_state == state
    assert not hasattr(window, "_binary_state_persistence")
    window._numeric_autosave.shutdown()


def test_numeric_autosave_captures_only_when_due_and_keeps_new_revision_dirty():
    _app()
    revision = [1]
    snapshots: list[int] = []
    persisted: list[ApplicationContextDTO] = []

    def snapshot():
        snapshots.append(revision[0])
        return ApplicationContextDTO(), revision[0]

    parent = QObject()
    scheduler = NumericAutosaveScheduler(
        snapshot,
        lambda: revision[0],
        lambda context: persisted.append(context) or Path("numeric.json"),
        120_000,
        parent,
    )
    saved = QSignalSpy(scheduler.saved)
    scheduler.mark_dirty("active-line", 1)
    scheduler.mark_dirty("active-line", 1)
    assert snapshots == []

    scheduler.flush_due()
    assert scheduler._pool.waitForDone(1_000)
    _app().processEvents()
    if saved.count() == 0:
        assert saved.wait(250)
    assert snapshots == [1]
    assert len(persisted) == 1

    revision[0] = 2
    scheduler._handle_saved(saved.at(0)[0])
    assert scheduler._pending is True
    scheduler.shutdown()


def test_numeric_close_barrier_skips_clean_context_and_joins_in_flight_save():
    _app()
    revision = [1]
    persisted: list[ApplicationContextDTO] = []
    parent = QObject()
    scheduler = NumericAutosaveScheduler(
        lambda: (ApplicationContextDTO(), revision[0]),
        lambda: revision[0],
        lambda context: persisted.append(context) or Path("numeric.json"),
        120_000,
        parent,
    )

    assert scheduler.flush_on_close().success is True
    assert persisted == []

    scheduler.mark_dirty("variables", revision[0])
    scheduler.flush_due()
    result = scheduler.flush_on_close()

    assert result.success is True
    assert len(persisted) == 1
    scheduler.shutdown()


def test_completion_catalog_pages_only_large_prefix_results():
    _app()
    values = tuple(f"variable_{index:06d}" for index in range(100_000))
    query = PrefixCatalog(values).query("variable_")
    model = PagedCompletionModel()
    model.set_items(query)

    assert len(query) == 100_000
    assert model.rowCount() == 128
    assert model.canFetchMore()
    model.fetchMore()
    assert model.rowCount() == 256

    model.set_items(PrefixCatalog(values[:511]).query("variable_"))
    assert model.rowCount() == 511
    assert not model.canFetchMore()
    model.set_items(PrefixCatalog(values[:512]).query("variable_"))
    assert model.rowCount() == 128
    assert model.canFetchMore()


def test_workspace_tables_keep_constant_permanent_widget_count_at_ten_thousand_rows():
    _app()
    dialog = WorkspaceTableDialog("Variables", ["Name", "Value", "Hex"], allow_add=True)
    initial_widgets = len(dialog.findChildren(QWidget))
    dialog.set_rows(
        [
            WorkspaceRow(index, (f"var_{index}", str(index), hex(index)))
            for index in range(10_000)
        ]
    )

    assert dialog.model.rowCount() == 10_000
    assert len(dialog.findChildren(QWidget)) == initial_widgets
    assert dialog.row_widgets == []


def test_workspace_dialog_controls_match_symbols_visual_metrics():
    _app()
    variables = WorkspaceTableDialog(
        "Variables",
        ["Name", "Value", "Hex"],
        allow_add=True,
    )
    logs = WorkspaceTableDialog("Logs", ["Instruction", "Result"])
    variables.show()
    _app().processEvents()

    assert variables.table.styleSheet() == ""
    assert variables.table.isSortingEnabled()
    assert not variables.table.horizontalHeader().isSortIndicatorShown()
    assert variables.name_input.minimumWidth() == WORKSPACE_TABLE_SIZE.FIELD_MIN_WIDTH
    assert variables.value_input.minimumWidth() == WORKSPACE_TABLE_SIZE.FIELD_MIN_WIDTH
    assert variables.name_input.height() == WORKSPACE_TABLE_SIZE.CONTROL_HEIGHT
    assert variables.remove_button.size().width() == WORKSPACE_TABLE_SIZE.ACTION_WIDTH
    assert variables.remove_button.height() == WORKSPACE_TABLE_SIZE.CONTROL_HEIGHT
    assert logs.remove_button.height() == WORKSPACE_TABLE_SIZE.CONTROL_HEIGHT
    assert logs.filter_input.height() == WORKSPACE_TABLE_SIZE.CONTROL_HEIGHT
    assert variables.name_input.width() == variables.value_input.width()
    assert (
        variables.add_button.x() - variables.value_input.geometry().right() - 1
        == WORKSPACE_TABLE_SPACING.VARIABLE_ENTRY
    )
    assert (
        variables.add_button.geometry().right()
        == variables.add_button.parentWidget().contentsRect().right()
    )


def test_workspace_filter_sort_selection_emits_stable_keys_without_model_reset():
    _app()
    dialog = WorkspaceTableDialog("Logs", ["Instruction", "Result"])
    reset = QSignalSpy(dialog.model.modelReset)
    removed = QSignalSpy(dialog.removeManyRequested)
    dialog.set_rows(
        [
            WorkspaceRow(10, ("charlie", "3")),
            WorkspaceRow(20, ("alpha", "1")),
            WorkspaceRow(30, ("bravo", "2")),
        ]
    )
    dialog.proxy.sort(0)
    dialog.filter_input.setText("a")
    selection = dialog.table.selectionModel()
    selection.select(
        dialog.proxy.index(0, 0),
        QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
    )
    selection.select(
        dialog.proxy.index(2, 0),
        QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
    )
    dialog.remove_button.click()

    assert reset.count() == 0
    assert removed.count() == 1
    assert set(removed.at(0)[0]) == {20, 10}
