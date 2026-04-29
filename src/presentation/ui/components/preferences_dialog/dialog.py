from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from src.application.dto.formatting_context import FormattingOutputDTO
from src.presentation.ui.components.preferences_dialog.constants import (
    PREFERENCES_DIALOG_MARGIN,
    PREFERENCES_DIALOG_SIZE,
    PREFERENCES_DIALOG_SPACING,
    PREFERENCES_DIALOG_TEXT,
)
from src.presentation.ui.components.preferences_dialog.constants.texts import FIELD_LABELS


class PreferencesDialog(QDialog):

    def __init__(
        self,
        formatting: dict[str, FormattingOutputDTO],
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(PREFERENCES_DIALOG_TEXT.TITLE)
        self.setModal(True)
        self.setMinimumSize(
            PREFERENCES_DIALOG_SIZE.MIN_WIDTH,
            PREFERENCES_DIALOG_SIZE.MIN_HEIGHT,
        )

        self._group_boxes: dict[str, QSpinBox] = {}
        self._zero_pad_boxes: dict[str, QCheckBox] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            PREFERENCES_DIALOG_MARGIN.ROOT_LEFT,
            PREFERENCES_DIALOG_MARGIN.ROOT_TOP,
            PREFERENCES_DIALOG_MARGIN.ROOT_RIGHT,
            PREFERENCES_DIALOG_MARGIN.ROOT_BOTTOM,
        )
        layout.setSpacing(PREFERENCES_DIALOG_SPACING.ROOT)

        title = QLabel(PREFERENCES_DIALOG_TEXT.TITLE)
        title.setObjectName("preferences-title")
        layout.addWidget(title)

        subtitle = QLabel(PREFERENCES_DIALOG_TEXT.SUBTITLE)
        subtitle.setObjectName("preferences-subtitle")
        layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setHorizontalSpacing(PREFERENCES_DIALOG_SPACING.GRID_HORIZONTAL)
        grid.setVerticalSpacing(PREFERENCES_DIALOG_SPACING.GRID_VERTICAL)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        grid.addWidget(QLabel(PREFERENCES_DIALOG_TEXT.FIELD_HEADER), 0, 0)
        grid.addWidget(QLabel(PREFERENCES_DIALOG_TEXT.GROUP_SIZE_HEADER), 0, 1)
        grid.addWidget(QLabel(PREFERENCES_DIALOG_TEXT.ZERO_PAD_HEADER), 0, 2)

        for row, (key, label_text) in enumerate(FIELD_LABELS.items(), start=1):
            group_size = QSpinBox()
            group_size.setRange(0, 64)
            group_size.setValue(formatting[key].group_size)

            zero_pad = QCheckBox()
            zero_pad.setChecked(formatting[key].zero_pad)

            self._group_boxes[key] = group_size
            self._zero_pad_boxes[key] = zero_pad

            grid.addWidget(QLabel(label_text), row, 0)
            grid.addWidget(group_size, row, 1)
            grid.addWidget(zero_pad, row, 2, Qt.AlignLeft)

        layout.addLayout(grid)

        buttons_row = QHBoxLayout()
        buttons_row.setContentsMargins(
            PREFERENCES_DIALOG_MARGIN.BUTTONS_LEFT,
            PREFERENCES_DIALOG_MARGIN.BUTTONS_TOP,
            PREFERENCES_DIALOG_MARGIN.BUTTONS_RIGHT,
            PREFERENCES_DIALOG_MARGIN.BUTTONS_BOTTOM,
        )
        buttons_row.setSpacing(PREFERENCES_DIALOG_SPACING.BUTTONS)

        cancel_button = QPushButton(PREFERENCES_DIALOG_TEXT.CANCEL)
        ok_button = QPushButton(PREFERENCES_DIALOG_TEXT.OK)

        for button in (ok_button, cancel_button):
            button.setMinimumWidth(PREFERENCES_DIALOG_SIZE.ACTION_BUTTON_WIDTH)
            button.setMinimumHeight(PREFERENCES_DIALOG_SIZE.ACTION_BUTTON_HEIGHT)

        ok_button.setObjectName("preferences-ok")
        cancel_button.setObjectName("preferences-cancel")

        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        buttons_row.addWidget(cancel_button, 0, Qt.AlignLeft)
        buttons_row.addStretch(1)
        buttons_row.addWidget(ok_button, 0, Qt.AlignRight)
        layout.addLayout(buttons_row)

    def selected_formatting(self) -> dict[str, FormattingOutputDTO]:
        return {
            key: FormattingOutputDTO(
                group_size=self._group_boxes[key].value(),
                zero_pad=self._zero_pad_boxes[key].isChecked(),
            )
            for key in self._group_boxes
        }
