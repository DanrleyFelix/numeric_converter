from collections.abc import Callable

from PySide6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QVBoxLayout

from src.modules.dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT


class BinaryWorkbenchGoToDialog(QDialog):
    def __init__(self, context: BinaryWorkbenchTabContextDTO, parent=None) -> None:
        super().__init__(parent)
        self._context = context
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.GO_TO)
        layout = _base_layout(self, BINARY_WORKBENCH_TEXT.GO_TO, BINARY_WORKBENCH_TEXT.GO_TO_SUBTITLE)
        self.target = QComboBox(self)
        self.target.setObjectName("binary-workbench-dialog-input")
        extra_offsets = [name for name in context.reference_offsets if name != "File"]
        self.target.addItems([
            BINARY_WORKBENCH_TEXT.FILE_OFFSET_TARGET,
            *extra_offsets,
            BINARY_WORKBENCH_TEXT.LBA_2048_TARGET,
            BINARY_WORKBENCH_TEXT.LBA_2334_TARGET,
            BINARY_WORKBENCH_TEXT.LBA_2352_TARGET,
            BINARY_WORKBENCH_TEXT.LABEL_TARGET,
            BINARY_WORKBENCH_TEXT.EQUATE_TARGET,
            BINARY_WORKBENCH_TEXT.VARIABLE_TARGET,
            BINARY_WORKBENCH_TEXT.INTERNAL_FILE_TARGET,
        ])
        self.value = _line_edit(self, BINARY_WORKBENCH_TEXT.VALUE)
        self.results = QListWidget(self)
        self.results.setObjectName("binary-workbench-search-results")
        resolve = QPushButton(BINARY_WORKBENCH_TEXT.GO_TO, self)
        resolve.setObjectName("preferences-cancel")
        resolve.clicked.connect(self.refresh_results)
        layout.addWidget(self.target)
        layout.addWidget(self.value)
        layout.addWidget(self.results)
        self.value.returnPressed.connect(self.refresh_results)
        self.results.itemDoubleClicked.connect(lambda _: self.accept())
        _finish(layout, resolve, self.accept)

    def selected_offsets(self) -> list[int]:
        if self.results.currentRow() >= 0:
            return [int(self.results.currentItem().text(), 0)]
        if self.results.count() > 0:
            return [int(self.results.item(index).text(), 0) for index in range(self.results.count())]
        return self._resolve_offsets()

    def refresh_results(self) -> None:
        self.results.clear()
        for offset in self._resolve_offsets():
            self.results.addItem(f"0x{offset:08X}")

    def _resolve_offsets(self) -> list[int]:
        raw = self.value.text().strip()
        target = self.target.currentText()
        if not raw:
            return []
        try:
            if target == BINARY_WORKBENCH_TEXT.FILE_OFFSET_TARGET:
                return [int(raw, 0)]
            if target in self._context.reference_offset_bases:
                base = int(self._context.reference_offset_bases.get(target, "0x0"), 0)
                return [int(raw, 0) - base]
            sectors = _lba_sectors()
            if target in sectors:
                return [int(raw, 0) * sectors[target]]
            if target == BINARY_WORKBENCH_TEXT.LABEL_TARGET:
                return _offsets_from_strings([self._context.labels.get(raw, "")])
            if target in {BINARY_WORKBENCH_TEXT.EQUATE_TARGET, BINARY_WORKBENCH_TEXT.VARIABLE_TARGET}:
                return _offsets_from_strings(self._context.symbol_offsets.get(raw, []))
            return []
        except ValueError:
            return []


class BinaryWorkbenchFindDialog(QDialog):
    def __init__(self, search: Callable[[str, str], list[int]], parent=None) -> None:
        super().__init__(parent)
        self._search = search
        self._offsets: list[int] = []
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.FIND)
        layout = _base_layout(self, BINARY_WORKBENCH_TEXT.FIND, BINARY_WORKBENCH_TEXT.FIND_SUBTITLE)
        self.mode = QComboBox(self)
        self.mode.setObjectName("binary-workbench-dialog-input")
        self.mode.addItems([BINARY_WORKBENCH_TEXT.FIND_ASSEMBLY, BINARY_WORKBENCH_TEXT.FIND_HEX_BYTES, BINARY_WORKBENCH_TEXT.FIND_DECODED_TEXT])
        self.query = _line_edit(self, BINARY_WORKBENCH_TEXT.VALUE)
        self.results = QListWidget(self)
        self.results.setObjectName("binary-workbench-search-results")
        layout.addWidget(self.mode)
        layout.addWidget(self.query)
        layout.addWidget(self.results)
        search_button = QPushButton(BINARY_WORKBENCH_TEXT.FIND, self)
        search_button.setObjectName("preferences-cancel")
        search_button.clicked.connect(self.refresh_results)
        self.query.returnPressed.connect(self.refresh_results)
        self.results.itemDoubleClicked.connect(lambda _: self.accept())
        _finish(layout, search_button, self.accept)

    def refresh_results(self) -> None:
        self._offsets = self._search(self.mode.currentText(), self.query.text().strip())
        self.results.clear()
        for offset in self._offsets:
            self.results.addItem(f"0x{offset:08X}")

    def selected_offset(self) -> int | None:
        if not self._offsets:
            self.refresh_results()
        if self.results.currentRow() >= 0:
            return self._offsets[self.results.currentRow()]
        return self._offsets[0] if self._offsets else None


class BinaryWorkbenchSelectBlockDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.SELECT_BLOCK)
        layout = _base_layout(self, BINARY_WORKBENCH_TEXT.SELECT_BLOCK, BINARY_WORKBENCH_TEXT.SELECT_BLOCK_SUBTITLE)
        self.start = _line_edit(self, BINARY_WORKBENCH_TEXT.START_OFFSET)
        self.end = _line_edit(self, BINARY_WORKBENCH_TEXT.END_OFFSET)
        self.length = _line_edit(self, BINARY_WORKBENCH_TEXT.LENGTH_BYTES)
        _finish(layout, self.start, self.end, self.length, self.accept)

    def selected_range(self) -> tuple[int, int] | None:
        try:
            if not self.start.text().strip():
                return None
            start = int(self.start.text().strip(), 0)
            if self.length.text().strip():
                return start, start + max(0, int(self.length.text().strip(), 0) - 1)
            return (start, int(self.end.text().strip(), 0)) if self.end.text().strip() else None
        except ValueError:
            return None


def _base_layout(dialog: QDialog, title_text: str, subtitle_text: str) -> QVBoxLayout:
    layout = QVBoxLayout(dialog)
    title = QLabel(title_text, dialog)
    title.setObjectName("preferences-title")
    subtitle = QLabel(subtitle_text, dialog)
    subtitle.setObjectName("preferences-subtitle")
    subtitle.setWordWrap(True)
    layout.addWidget(title)
    layout.addWidget(subtitle)
    return layout


def _finish(layout: QVBoxLayout, *widgets) -> None:
    callback = widgets[-1]
    action_button = widgets[-2] if len(widgets) > 1 and isinstance(widgets[-2], QPushButton) else None
    content_widgets = widgets[:-2] if action_button is not None else widgets[:-1]
    for widget in content_widgets:
        layout.addWidget(widget)
    ok = QPushButton("OK")
    ok.setObjectName("preferences-ok")
    ok.clicked.connect(callback)
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    if action_button is not None:
        row.addWidget(action_button)
    row.addStretch(1)
    row.addWidget(ok)
    layout.addLayout(row)


def _line_edit(parent: QDialog, placeholder: str) -> QLineEdit:
    editor = QLineEdit(parent)
    editor.setObjectName("binary-workbench-dialog-input")
    editor.setPlaceholderText(placeholder)
    return editor


def _lba_sectors() -> dict[str, int]:
    return {
        BINARY_WORKBENCH_TEXT.LBA_2048_TARGET: 2048,
        BINARY_WORKBENCH_TEXT.LBA_2334_TARGET: 2334,
        BINARY_WORKBENCH_TEXT.LBA_2352_TARGET: 2352,
    }


def _offsets_from_strings(values: list[str]) -> list[int]:
    offsets: list[int] = []
    for value in values:
        try:
            offsets.append(int(value, 0))
        except ValueError:
            continue
    return offsets
