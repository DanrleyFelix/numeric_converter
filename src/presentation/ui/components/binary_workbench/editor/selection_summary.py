import re

from PySide6.QtWidgets import QHBoxLayout, QLabel

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)

_SELECTION = re.compile(
    r"Offset: 0x(?P<offset>[0-9A-F]+) \| "
    r"Selected: 0x(?P<first>[0-9A-F]+)\.\.0x(?P<last>[0-9A-F]+) \| "
    r"Length: (?P<length>\d+) bytes"
)
_OFFSET = re.compile(r"Offset: 0x(?P<offset>[0-9A-F]+)")


def selection_summary_label(text: str, parent) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName("binary-workbench-selection")
    return label


def selection_summary_footer(parent) -> tuple[QHBoxLayout, tuple[QLabel, QLabel, QLabel, QLabel]]:
    labels = tuple(selection_summary_label("", parent) for _ in range(4))
    footer = QHBoxLayout()
    footer.setContentsMargins(0, BINARY_WORKBENCH_LAYOUT.SUMMARY_TOP_MARGIN, 0, 0)
    footer.setSpacing(BINARY_WORKBENCH_LAYOUT.SUMMARY_LABEL_SPACING)
    for label in labels:
        footer.addWidget(label)
    footer.addStretch(1)
    return footer, labels


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
