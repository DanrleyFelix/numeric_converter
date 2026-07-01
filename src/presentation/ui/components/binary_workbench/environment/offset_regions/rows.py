from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLineEdit, QPlainTextEdit, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from src.modules.binary_workbench_dtos import BinaryWorkbenchOffsetRegionDTO
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_dialog_action,
    configure_binary_workbench_input,
    configure_binary_workbench_line_edit,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_DIALOG_LAYOUT,
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.dialog_context_menu import (
    configure_dialog_text_context_menu,
)
from src.presentation.ui.components.binary_workbench.environment.offset_regions.constants import (
    OFFSET_REGIONS_SIZE,
    OFFSET_REGIONS_SPACING,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.lba_filesystem_widgets import (
    LbaRemoveRowButton,
    lba_button,
    lba_input,
)
from src.presentation.ui.components.binary_workbench.input_validators import set_hex_value_validator
from src.presentation.ui.components.workspace_table.constants.layout import WORKSPACE_TABLE_SIZE


@dataclass
class _OffsetRow:
    name: QLineEdit
    offset: QLineEdit
    details: str
    details_loaded: bool
    source_name: str | None
    source_offset: int | None
    widget: QWidget
    remove_slot: QWidget


class OffsetRegionsRowsMixin:
    def mappings(self) -> list[BinaryWorkbenchOffsetRegionDTO]:
        regions: list[BinaryWorkbenchOffsetRegionDTO] = []
        for row in self._rows:
            try:
                offset = int(row.offset.text().strip(), 16)
            except ValueError:
                continue
            if row.name.text().strip() and offset >= 0:
                details = row.details if row.details_loaded else ""
                regions.append(BinaryWorkbenchOffsetRegionDTO(
                    row.name.text().strip(),
                    offset,
                    details,
                    row.details_loaded,
                    row.source_name,
                    row.source_offset,
                ))
        return regions

    def _append_from_entry(self) -> None:
        self._append_row(self.name.text(), self.offset.text(), "")
        self.name.clear()
        self.offset.clear()
        self._apply_filter()

    def _clear_rows(self) -> None:
        for row in self._rows:
            row.widget.deleteLater()
            row.remove_slot.deleteLater()
        self._rows.clear()

    def _append_row(
        self,
        name: str,
        offset: str,
        details: str,
        details_loaded: bool = True,
        source_name: str | None = None,
        source_offset: int | None = None,
    ) -> None:
        widget = QWidget(self.body)
        widget.setObjectName("workspace-row")
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.EMPTY_MARGINS)
        layout.setSpacing(BINARY_WORKBENCH_DIALOG_LAYOUT.ROW_SPACING)
        name_edit = lba_input(BINARY_WORKBENCH_TEXT.OFFSET_NAME, widget, name, BINARY_WORKBENCH_LAYOUT.SHARED_INPUT_WIDTH)
        offset_edit = lba_input(BINARY_WORKBENCH_TEXT.OFFSET_VALUE, widget, offset, BINARY_WORKBENCH_LAYOUT.SHARED_INPUT_WIDTH)
        set_hex_value_validator(offset_edit)
        configure_binary_workbench_input(name_edit, BINARY_WORKBENCH_LAYOUT.SHARED_INPUT_WIDTH)
        configure_binary_workbench_input(offset_edit, BINARY_WORKBENCH_LAYOUT.SHARED_INPUT_WIDTH)
        configure_binary_workbench_line_edit(name_edit, BINARY_WORKBENCH_LAYOUT.SHARED_INPUT_WIDTH)
        configure_binary_workbench_line_edit(offset_edit, BINARY_WORKBENCH_LAYOUT.SHARED_INPUT_WIDTH)
        details_button = lba_button(BINARY_WORKBENCH_TEXT.DETAILS, "", widget)
        go_to = lba_button(BINARY_WORKBENCH_TEXT.GO_TO, "", widget)
        for button in (details_button, go_to):
            configure_binary_workbench_dialog_action(button)
        remove_slot = _remove_slot(self.remove_body)
        remove = LbaRemoveRowButton(remove_slot)
        remove.setFixedSize(
            WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_WIDTH,
            WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_HEIGHT,
        )
        row = _OffsetRow(name_edit, offset_edit, details, details_loaded, source_name, source_offset, widget, remove_slot)
        name_edit.textChanged.connect(self._apply_filter)
        offset_edit.textChanged.connect(self._apply_filter)
        details_button.clicked.connect(lambda: self._edit_details(row))
        go_to.clicked.connect(lambda: self._go_to_offset(offset_edit.text()))
        remove.clicked.connect(lambda: self._remove_row(row))
        layout.addWidget(name_edit)
        layout.addWidget(offset_edit)
        layout.addWidget(details_button, 0, Qt.AlignVCenter)
        layout.addWidget(go_to, 0, Qt.AlignVCenter)
        remove_slot.layout().addWidget(remove, 0, Qt.AlignCenter)
        self._rows.append(row)
        self.body_layout.addWidget(widget)
        self.remove_layout.addWidget(remove_slot)

    def _edit_details(self, row: _OffsetRow) -> None:
        details = self._row_details(row)
        dialog = OffsetRegionDetailsDialog(details, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            row.details = dialog.details()
            row.details_loaded = True
            self._apply_filter()

    def _row_details(self, row: _OffsetRow) -> str:
        if row.details_loaded:
            return row.details
        try:
            offset = int(row.offset.text().strip(), 16)
        except ValueError:
            return ""
        source_name = row.source_name or row.name.text().strip()
        source_offset = row.source_offset if row.source_offset is not None else offset
        loader = getattr(self, "_details_loader", None)
        row.details = loader(source_name, source_offset) if loader is not None else row.details
        row.details_loaded = True
        return row.details

    def _go_to_offset(self, value: str) -> None:
        try:
            self.goToRequested.emit(int(value.strip(), 16))
        except ValueError:
            return

    def _remove_row(self, row: _OffsetRow) -> None:
        self._rows.remove(row)
        row.widget.deleteLater()
        row.remove_slot.deleteLater()

    def _apply_filter(self) -> None:
        query = self.filter_input.text().strip().casefold()
        for row in self._rows:
            details = row.details if row.details_loaded else ""
            haystack = f"{row.name.text()} {row.offset.text()} {details}".casefold()
            visible = not query or query in haystack
            row.widget.setVisible(visible)
            row.remove_slot.setVisible(visible)


class OffsetRegionDetailsDialog(QDialog):
    def __init__(self, details: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.DETAILS)
        self.setFixedSize(
            OFFSET_REGIONS_SIZE.DETAILS_DIALOG_WIDTH,
            OFFSET_REGIONS_SIZE.DETAILS_DIALOG_HEIGHT,
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.CONTENT_MARGINS)
        layout.setSpacing(OFFSET_REGIONS_SPACING.DETAILS_DIALOG)
        self.editor = QPlainTextEdit(self)
        configure_dialog_text_context_menu(self.editor)
        self.editor.setPlainText(details)
        layout.addWidget(self.editor, 1)
        footer = QHBoxLayout()
        footer.setSpacing(OFFSET_REGIONS_SPACING.DETAILS_DIALOG)
        cancel = _details_action(BINARY_WORKBENCH_TEXT.CANCEL, self)
        ok = _details_action(BINARY_WORKBENCH_TEXT.OK, self)
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        footer.addWidget(cancel)
        footer.addStretch(1)
        footer.addWidget(ok)
        layout.addLayout(footer)

    def details(self) -> str:
        return self.editor.toPlainText()


def _details_action(text: str, parent: QWidget) -> QPushButton:
    button = QPushButton(text, parent)
    configure_binary_workbench_dialog_action(button)
    button.setCursor(Qt.PointingHandCursor)
    button.setFocusPolicy(Qt.StrongFocus)
    return button


def _remove_slot(parent: QWidget) -> QWidget:
    slot = QWidget(parent)
    slot.setFixedWidth(WORKSPACE_TABLE_SIZE.REMOVE_GUTTER_WIDTH)
    slot.setFixedHeight(BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)
    layout = QVBoxLayout(slot)
    layout.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.EMPTY_MARGINS)
    return slot
