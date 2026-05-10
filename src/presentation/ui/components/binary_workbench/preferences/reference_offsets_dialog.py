from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT

_MAX_EXTRA_OFFSETS = 3


class BinaryWorkbenchReferenceOffsetsDialog(QDialog):
    def __init__(
        self,
        reference_offsets: list[str],
        reference_offset_bases: dict[str, str],
        visible_columns: dict[str, bool],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.REFERENCE_OFFSETS)
        layout = QVBoxLayout(self)
        title = QLabel(BINARY_WORKBENCH_TEXT.REFERENCE_OFFSETS, self)
        title.setObjectName("preferences-title")
        subtitle = QLabel(BINARY_WORKBENCH_TEXT.REFERENCE_OFFSETS_SUBTITLE, self)
        subtitle.setObjectName("preferences-subtitle")
        subtitle.setWordWrap(True)
        self._rows: list[tuple[QLineEdit, QLineEdit, QCheckBox]] = []
        layout.addWidget(title)
        layout.addWidget(subtitle)
        for name in [value for value in reference_offsets if value != "File"][:_MAX_EXTRA_OFFSETS]:
            self._append_row(layout, name, reference_offset_bases.get(name, "0x00000000"), visible_columns.get(name, True))
        for _ in range(_MAX_EXTRA_OFFSETS - len(self._rows)):
            self._append_row(layout, "", "0x00000000", False)
        ok = QPushButton("OK", self)
        ok.setObjectName("preferences-ok")
        ok.setFocusPolicy(Qt.NoFocus)
        ok.setCursor(Qt.PointingHandCursor)
        ok.clicked.connect(self.accept)
        layout.addWidget(ok, 0, Qt.AlignRight)

    def values(self) -> tuple[list[str], dict[str, str], dict[str, bool]]:
        offsets = ["File"]
        bases = {"File": "0x00000000"}
        visible = {"File": True}
        for name_field, base_field, visible_box in self._rows:
            name = name_field.text().strip()
            if not name:
                continue
            offsets.append(name)
            bases[name] = base_field.text().strip() or "0x00000000"
            visible[name] = visible_box.isChecked()
        return offsets, bases, visible

    def _append_row(
        self,
        parent_layout: QVBoxLayout,
        name: str,
        base: str,
        visible: bool,
    ) -> None:
        row = QHBoxLayout()
        name_field = QLineEdit(name, self)
        name_field.setObjectName("binary-workbench-dialog-input")
        name_field.setPlaceholderText(BINARY_WORKBENCH_TEXT.REFERENCE_NAME)
        base_field = QLineEdit(base, self)
        base_field.setObjectName("binary-workbench-dialog-input")
        base_field.setPlaceholderText(BINARY_WORKBENCH_TEXT.REFERENCE_BASE)
        visible_box = QCheckBox(BINARY_WORKBENCH_TEXT.REFERENCE_VISIBLE, self)
        visible_box.setChecked(visible)
        visible_box.setCursor(Qt.PointingHandCursor)
        row.addWidget(name_field, 2)
        row.addWidget(base_field, 2)
        row.addWidget(visible_box, 1)
        self._rows.append((name_field, base_field, visible_box))
        parent_layout.addLayout(row)
