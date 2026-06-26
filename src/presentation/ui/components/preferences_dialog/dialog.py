from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QVBoxLayout,
)

from src.modules.converter_dtos import FormattingOutputDTO
from src.presentation.ui.components.preferences_dialog.combo_delegate import (
    PreferencesComboItemDelegate,
)
from src.presentation.ui.components.preferences_dialog.constants import (
    PREFERENCES_DIALOG_MARGIN,
    PREFERENCES_DEFAULT_COPY_FIELD,
    PREFERENCES_GROUP_SIZE_VALUES,
    PREFERENCES_DIALOG_SIZE,
    PREFERENCES_DIALOG_SPACING,
    PREFERENCES_DIALOG_TEXT,
)
from src.presentation.ui.components.preferences_dialog.constants.texts import FIELD_LABELS


class PreferencesDialog(QDialog):

    def __init__(
        self,
        formatting: dict[str, FormattingOutputDTO],
        default_copy_field: str = PREFERENCES_DEFAULT_COPY_FIELD,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(PREFERENCES_DIALOG_TEXT.TITLE)
        self.setModal(True)
        self.setFixedSize(
            PREFERENCES_DIALOG_SIZE.WIDTH,
            PREFERENCES_DIALOG_SIZE.HEIGHT,
        )

        self._group_boxes: dict[str, QComboBox] = {}
        self._zero_pad_boxes: dict[str, QCheckBox] = {}
        self._copy_field_by_label = {label: key for key, label in FIELD_LABELS.items()}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            PREFERENCES_DIALOG_MARGIN.ROOT_LEFT,
            PREFERENCES_DIALOG_MARGIN.ROOT_TOP,
            PREFERENCES_DIALOG_MARGIN.ROOT_RIGHT,
            PREFERENCES_DIALOG_MARGIN.ROOT_BOTTOM,
        )
        layout.setSpacing(PREFERENCES_DIALOG_SPACING.ROOT)
        layout.setAlignment(Qt.AlignTop)

        self.default_copy = QComboBox()
        self.default_copy.setObjectName("preferences-copy-placeholder")
        self.default_copy.setFixedWidth(PREFERENCES_DIALOG_SIZE.DEFAULT_COPY_WIDTH)
        self.default_copy.addItems(list(FIELD_LABELS.values()))
        current_copy = FIELD_LABELS.get(
            default_copy_field,
            FIELD_LABELS[PREFERENCES_DEFAULT_COPY_FIELD],
        )
        self.default_copy.setCurrentText(current_copy)
        self.default_copy.setItemDelegate(PreferencesComboItemDelegate(self.default_copy))
        self.default_copy.setFocusPolicy(Qt.NoFocus)
        self.default_copy.setCursor(Qt.PointingHandCursor)

        default_copy_row = QHBoxLayout()
        default_copy_row.setContentsMargins(0, 0, 0, 0)
        default_copy_row.setSpacing(PREFERENCES_DIALOG_SPACING.GRID_HORIZONTAL)
        default_copy_row.addWidget(QLabel(PREFERENCES_DIALOG_TEXT.DEFAULT_COPY_LABEL))
        default_copy_row.addWidget(self.default_copy)
        default_copy_row.addStretch(1)
        layout.addLayout(default_copy_row)
        layout.addSpacing(PREFERENCES_DIALOG_SPACING.DEFAULT_COPY_TO_HEADERS)

        grid = QGridLayout()
        grid.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        grid.setHorizontalSpacing(PREFERENCES_DIALOG_SPACING.GRID_HORIZONTAL)
        grid.setVerticalSpacing(PREFERENCES_DIALOG_SPACING.GRID_LAYOUT)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 0)
        grid.setColumnStretch(2, 1)

        header_row = PREFERENCES_DIALOG_SPACING.GRID_HEADER_ROW
        grid.addWidget(QLabel(PREFERENCES_DIALOG_TEXT.FIELD_HEADER), header_row, 0)
        grid.addWidget(QLabel(PREFERENCES_DIALOG_TEXT.GROUP_SIZE_HEADER), header_row, 1)
        grid.addWidget(QLabel(PREFERENCES_DIALOG_TEXT.ZERO_PAD_HEADER), header_row, 2)
        grid.setRowMinimumHeight(
            PREFERENCES_DIALOG_SPACING.GRID_HEADER_SPACER_ROW,
            PREFERENCES_DIALOG_SPACING.GRID_HEADER,
        )

        for index, (key, label_text) in enumerate(FIELD_LABELS.items()):
            row = (
                PREFERENCES_DIALOG_SPACING.GRID_FIRST_DATA_ROW
                + index * PREFERENCES_DIALOG_SPACING.GRID_ROW_STEP
            )
            if index:
                grid.setRowMinimumHeight(
                    row - 1,
                    PREFERENCES_DIALOG_SPACING.GRID_IDENTICAL_ROWS,
                )
            group_size = QComboBox()
            group_size.setObjectName("preferences-group-size")
            group_size.setFixedWidth(PREFERENCES_DIALOG_SIZE.GROUP_SIZE_WIDTH)
            group_size.addItems(str(value) for value in PREFERENCES_GROUP_SIZE_VALUES)
            group_size.setCurrentText(
                str(_closest_group_size(formatting[key].group_size))
            )
            group_size.setItemDelegate(PreferencesComboItemDelegate(group_size))
            group_size.setFocusPolicy(Qt.NoFocus)
            group_size.setCursor(Qt.PointingHandCursor)

            zero_pad = QCheckBox()
            zero_pad.setChecked(formatting[key].zero_pad)

            self._group_boxes[key] = group_size
            self._zero_pad_boxes[key] = zero_pad

            grid.addWidget(QLabel(label_text), row, 0)
            grid.addWidget(group_size, row, 1)
            grid.addWidget(zero_pad, row, 2, Qt.AlignLeft)

        layout.addLayout(grid)
        layout.addSpacing(PREFERENCES_DIALOG_SPACING.ITEMS_TO_BUTTONS)

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
                group_size=int(self._group_boxes[key].currentText()),
                zero_pad=self._zero_pad_boxes[key].isChecked(),
            )
            for key in self._group_boxes
        }

    def selected_default_copy_field(self) -> str:
        return self._copy_field_by_label.get(
            self.default_copy.currentText(),
            PREFERENCES_DEFAULT_COPY_FIELD,
        )


def _closest_group_size(value: int) -> int:
    if value in PREFERENCES_GROUP_SIZE_VALUES:
        return value
    return min(PREFERENCES_GROUP_SIZE_VALUES, key=lambda item: abs(item - value))
