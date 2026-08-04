import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, QRect, Signal, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QLabel,
    QLineEdit,
    QPushButton,
    QStyleOptionViewItem,
    QTableView,
    QWidget,
)

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT
from src.presentation.ui.components.binary_workbench.button_icon_painting import (
    ICON_TEXT_SPACING_PROPERTY,
)
from src.presentation.ui.components.binary_workbench.environment import (
    BinaryWorkbenchSymbolOffsetsDialog,
    BinaryWorkbenchSymbolsDialog,
)
from src.presentation.ui.components.binary_workbench.environment import (
    symbols_dialog_rows as rows_module,
)
from src.presentation.ui.components.binary_workbench.input_validators import (
    PythonIdentifierValidator,
)


def _app() -> QApplication:
    """Return the shared offscreen Qt application used by dialog tests."""

    return QApplication.instance() or QApplication([])


def test_symbols_table_virtualizes_rows_without_per_symbol_widgets():
    _app()
    small = BinaryWorkbenchSymbolsDialog({"one": "1"}, {}, {})
    large = BinaryWorkbenchSymbolsDialog(
        {f"symbol_{index}": str(index) for index in range(1000)},
        {},
        {},
    )

    assert isinstance(large.table, QTableView)
    assert large.table.showGrid() is True
    assert large.symbols_model.rowCount() == 1000
    assert len(small.findChildren(QWidget)) == len(large.findChildren(QWidget))
    assert len(large.findChildren(QLineEdit)) == 3
    assert len(large.findChildren(QPushButton)) == 5
    assert large.findChildren(QWidget, "workspace-row") == []
    assert [label.text() for label in large.findChildren(QLabel) if label.text()] == []
    margins = large.shell.layout().contentsMargins()
    assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (
        20,
        20,
        20,
        20,
    )


def test_fixed_symbol_actions_use_project_icons():
    """Keep the four requested actions visually identifiable."""

    _app()
    dialog = BinaryWorkbenchSymbolsDialog({"one": "1"}, {}, {})
    buttons = {button.text(): button for button in dialog.findChildren(QPushButton)}

    for text in (
        BINARY_WORKBENCH_TEXT.LOAD,
        BINARY_WORKBENCH_TEXT.SAVE,
        BINARY_WORKBENCH_TEXT.SYMBOL_OFFSETS,
        BINARY_WORKBENCH_TEXT.SYMBOL_ADD,
    ):
        assert not buttons[text].icon().isNull()
        assert (
            buttons[text].property(ICON_TEXT_SPACING_PROPERTY)
            == BINARY_WORKBENCH_LAYOUT.SYMBOL_ACTION_ICON_TEXT_SPACING
        )


def test_offsets_action_maps_filter_and_sort_selection_to_source(monkeypatch):
    _app()
    opened: list[tuple[str, list[str]]] = []
    requested: list[str] = []

    class OffsetsDialog(QObject):
        goToRequested = Signal(int)

        def __init__(self, name, offsets, parent=None):
            super().__init__(parent)
            opened.append((name, offsets))

        def exec(self):
            return 0

    monkeypatch.setattr(rows_module, "BinaryWorkbenchSymbolOffsetsDialog", OffsetsDialog)
    dialog = BinaryWorkbenchSymbolsDialog(
        {"alpha": "1", "beta": "2", "gamma": "3"},
        {},
        {},
        offsets_provider=lambda name: ("tab", requested.append(name) or [f"{name}-offset"]),
    )
    dialog.filter_input.setText("beta")
    dialog.table.selectRow(0)
    dialog.offsets_button.click()

    assert requested[-1] == "beta"
    assert opened[-1] == ("beta", ["beta-offset"])

    dialog.filter_input.clear()
    dialog.table.sortByColumn(0, Qt.SortOrder.DescendingOrder)
    dialog.table.selectRow(0)
    dialog.offsets_button.click()

    assert requested[-1] == "gamma"
    assert opened[-1] == ("gamma", ["gamma-offset"])


def test_symbol_table_tracks_row_hover_and_keeps_cell_double_click_editing():
    """Hover whole rows without losing the cell pointed to by a double click."""

    app = _app()
    dialog = BinaryWorkbenchSymbolsDialog({"alpha": "1", "beta": "2"}, {}, {})
    dialog.show()
    app.processEvents()
    target = dialog.symbols_proxy.index(0, dialog.symbols_model.VALUE_COLUMN)
    target_center = dialog.table.visualRect(target).center()

    QTest.mouseMove(dialog.table.viewport(), target_center)
    assert dialog.table.hovered_row == target.row()
    assert dialog.table.indexAt(target_center) == target
    assert dialog.table.editTriggers() & QAbstractItemView.EditTrigger.DoubleClicked

    QTest.mouseClick(
        dialog.table.viewport(),
        Qt.MouseButton.LeftButton,
        pos=target_center,
    )
    app.processEvents()

    assert dialog.table.currentIndex() == target
    dialog.close()


def test_symbol_mutations_emit_incremental_model_signals_only():
    _app()
    dialog = BinaryWorkbenchSymbolsDialog({"alpha": "1"}, {}, {})
    inserted: list[tuple[int, int]] = []
    removed: list[tuple[int, int]] = []
    changed: list[tuple[int, int]] = []
    resets: list[bool] = []
    dialog.symbols_model.rowsInserted.connect(
        lambda _parent, first, last: inserted.append((first, last))
    )
    dialog.symbols_model.rowsRemoved.connect(
        lambda _parent, first, last: removed.append((first, last))
    )
    dialog.symbols_model.dataChanged.connect(
        lambda first, last, _roles: changed.append((first.row(), last.row()))
    )
    dialog.symbols_model.modelReset.connect(lambda: resets.append(True))

    dialog._merge_rows({"beta": "2"})
    value_index = dialog.symbols_model.index(0, dialog.symbols_model.VALUE_COLUMN)
    dialog.symbols_model.setData(value_index, "10")
    dialog._select_symbol(dialog.symbols_model.record_at(1).symbol_id)
    dialog._remove_selected_symbol()

    assert inserted == [(1, 1)]
    assert changed == [(0, 0)]
    assert removed == [(1, 1)]
    assert resets == []


def test_remove_action_uses_source_identity_after_filtering():
    _app()
    dialog = BinaryWorkbenchSymbolsDialog(
        {"alpha": "1", "beta": "2", "gamma": "3"},
        {},
        {},
    )
    dialog.filter_input.setText("beta")
    dialog.table.selectRow(0)

    dialog.remove_button.click()

    assert dialog.values()[0] == {"alpha": "1", "gamma": "3"}


def test_sort_repositions_an_edit_without_changing_selected_identity():
    _app()
    dialog = BinaryWorkbenchSymbolsDialog({"alpha": "1", "beta": "2"}, {}, {})
    dialog.table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
    dialog.table.selectRow(1)
    selected_id = dialog._selected_symbol_id()
    source_row = dialog.symbols_model.row_for_id(selected_id)

    dialog.symbols_model.setData(
        dialog.symbols_model.index(source_row, dialog.symbols_model.NAME_COLUMN),
        "aardvark",
    )

    assert dialog._selected_symbol_id() == selected_id
    assert dialog._selected_record().name == "aardvark"


def test_transient_cell_delegate_reuses_name_validator_only():
    _app()
    dialog = BinaryWorkbenchSymbolsDialog({"alpha": "1"}, {}, {})
    delegate = dialog.table.itemDelegate()
    name_editor = delegate.createEditor(
        dialog.table,
        None,
        dialog.symbols_proxy.index(0, dialog.symbols_model.NAME_COLUMN),
    )
    value_editor = delegate.createEditor(
        dialog.table,
        None,
        dialog.symbols_proxy.index(0, dialog.symbols_model.VALUE_COLUMN),
    )

    assert isinstance(name_editor.validator(), PythonIdentifierValidator)
    assert value_editor.validator() is None
    assert name_editor.alignment() == Qt.AlignmentFlag.AlignCenter
    assert value_editor.alignment() == Qt.AlignmentFlag.AlignCenter
    assert name_editor.objectName() == "binary-workbench-environment-cell-editor"
    assert value_editor.objectName() == "binary-workbench-environment-cell-editor"
    assert (
        dialog.table.horizontalHeader().height()
        == BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT
    )
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 220, BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)
    delegate.updateEditorGeometry(
        name_editor,
        option,
        dialog.symbols_proxy.index(0, dialog.symbols_model.NAME_COLUMN),
    )
    assert name_editor.geometry() == option.rect
    assert (
        dialog.symbols_model.data(
            dialog.symbols_model.index(0, dialog.symbols_model.NAME_COLUMN),
            Qt.ItemDataRole.TextAlignmentRole,
        )
        == Qt.AlignmentFlag.AlignCenter
    )


def test_batch_merge_refreshes_proxy_filter_once():
    _app()
    dialog = BinaryWorkbenchSymbolsDialog({"alpha": "1"}, {}, {})
    dialog.filter_input.setText("batch")
    inserted: list[tuple[int, int]] = []
    resets: list[bool] = []
    dialog.symbols_model.rowsInserted.connect(
        lambda _parent, first, last: inserted.append((first, last))
    )
    dialog.symbols_model.modelReset.connect(lambda: resets.append(True))

    dialog._merge_rows({f"batch_{index}": str(index) for index in range(100)})

    assert inserted == [(1, 100)]
    assert resets == []
    assert dialog.symbols_proxy.rowCount() == 100
    assert dialog.symbols_model.rowCount() == 101


def test_offsets_actions_follow_valid_visible_selection():
    _app()
    dialog = BinaryWorkbenchSymbolsDialog({"alpha": "1", "beta": "2"}, {}, {})

    assert dialog.offsets_button.isEnabled() is False
    assert dialog.remove_button.isEnabled() is False
    dialog.table.selectRow(0)
    assert dialog.offsets_button.isEnabled() is True
    assert dialog.remove_button.isEnabled() is True

    dialog.filter_input.setText("missing")
    assert dialog.offsets_button.isEnabled() is False
    assert dialog.remove_button.isEnabled() is False


def test_open_offsets_view_is_invalidated_without_requerying(monkeypatch):
    _app()
    stale: list[bool] = []
    provider_calls: list[str] = []

    class OffsetsDialog(QObject):
        goToRequested = Signal(int)

        def __init__(self, _name, _offsets, parent=None):
            super().__init__(parent)
            self.parent_dialog = parent

        def exec(self):
            self.parent_dialog.invalidate_offsets_context()
            return 0

        def mark_stale(self):
            stale.append(True)

    monkeypatch.setattr(rows_module, "BinaryWorkbenchSymbolOffsetsDialog", OffsetsDialog)
    dialog = BinaryWorkbenchSymbolsDialog(
        {"global_symbol": "1"},
        {},
        {},
        offsets_provider=lambda name: (
            "active-tab",
            provider_calls.append(name) or ["0x00000010"],
        ),
    )
    dialog.table.selectRow(0)
    dialog.offsets_button.click()

    assert provider_calls == ["global_symbol"]
    assert stale == [True]


def test_offsets_dialog_replaces_old_context_with_non_navigable_stale_state():
    _app()
    dialog = BinaryWorkbenchSymbolOffsetsDialog("global_symbol", ["0x00000010"])
    navigated: list[int] = []
    dialog.goToRequested.connect(navigated.append)

    dialog.mark_stale()
    item = dialog.offsets.item(0)
    dialog.offsets.itemClicked.emit(item)

    assert dialog.offsets.count() == 1
    assert item.text() == BINARY_WORKBENCH_TEXT.SYMBOL_OFFSETS_STALE
    assert not item.flags() & Qt.ItemFlag.ItemIsEnabled
    assert dialog.offsets.spacing() == 0
    assert dialog.offsets.uniformItemSizes() is True
    assert item.sizeHint().height() == dialog.offsets.fontMetrics().height() * 2
    assert navigated == []
