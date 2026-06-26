import re

from PySide6.QtWidgets import QHBoxLayout, QLabel

from src.modules.constants import HEX_UPPER_DIGIT_PATTERN
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)

_SELECTION = re.compile(
    rf"Offset: 0x(?P<offset>{HEX_UPPER_DIGIT_PATTERN}+) \| "
    rf"Selected: 0x(?P<first>{HEX_UPPER_DIGIT_PATTERN}+)\.\.0x(?P<last>{HEX_UPPER_DIGIT_PATTERN}+) \| "
    r"Length: (?P<length>\d+) bytes"
)
_OFFSET = re.compile(rf"Offset: 0x(?P<offset>{HEX_UPPER_DIGIT_PATTERN}+)")


def selection_summary_label(text: str, parent) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName("binary-workbench-selection")
    return label


def internal_file_summary_label(parent) -> QLabel:
    label = QLabel("", parent)
    label.setObjectName("binary-workbench-internal-file-summary")
    label.setVisible(False)
    return label


def selection_summary_footer(parent) -> tuple[QHBoxLayout, tuple[QLabel, QLabel, QLabel, QLabel, QLabel]]:
    labels = tuple(selection_summary_label("", parent) for _ in range(4))
    internal = internal_file_summary_label(parent)
    footer = QHBoxLayout()
    footer.setContentsMargins(0, BINARY_WORKBENCH_LAYOUT.SUMMARY_TOP_MARGIN, 0, 0)
    footer.setSpacing(BINARY_WORKBENCH_LAYOUT.SUMMARY_LABEL_SPACING)
    for label in labels:
        footer.addWidget(label)
    footer.addWidget(internal)
    footer.addStretch(1)
    return footer, (*labels, internal)


def update_selection_summary(labels: tuple[QLabel, QLabel, QLabel], text: str) -> None:
    offset, selected, length = labels
    match = _SELECTION.fullmatch(text)
    if match is None:
        cursor = _OFFSET.fullmatch(text)
        offset.setText(
            BINARY_WORKBENCH_TEXT.OFFSET_SUMMARY_TEMPLATE.format(offset=cursor["offset"])
            if cursor is not None
            else BINARY_WORKBENCH_TEXT.OFFSET_SUMMARY_EMPTY
        )
        selected.setText(BINARY_WORKBENCH_TEXT.SELECTED_BLOCK_SUMMARY_EMPTY)
        length.setText(BINARY_WORKBENCH_TEXT.LENGTH_SUMMARY_EMPTY)
        return
    first = match["first"]
    last = match["last"]
    offset.setText(BINARY_WORKBENCH_TEXT.OFFSET_SUMMARY_TEMPLATE.format(offset=match["offset"]))
    selected.setText(
        BINARY_WORKBENCH_TEXT.SELECTED_BLOCK_SUMMARY_TEMPLATE.format(first=first, last=last)
    )
    length.setText(BINARY_WORKBENCH_TEXT.LENGTH_SUMMARY_TEMPLATE.format(length=match["length"]))
