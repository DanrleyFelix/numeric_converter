from __future__ import annotations

import re

from PySide6.QtGui import QSyntaxHighlighter

from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    BYTE_TOKEN,
    EQUATE_TOKEN,
    HEX_TOKEN,
    REGISTER_TOKEN,
    VARIABLE_TOKEN,
    code_without_label,
    invalid_instruction,
    mnemonic_color,
    register_color,
    text_format,
)


class BytesHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text: str) -> None:
        even = text_format("#EAEAF5")
        odd = text_format("#8FA6FF")
        for index, match in enumerate(BYTE_TOKEN.finditer(text)):
            self.setFormat(
                match.start(),
                match.end() - match.start(),
                even if index % 2 == 0 else odd,
            )


class InstructionHighlighter(QSyntaxHighlighter):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self._labels: dict[str, str] = {}
        self._variables: dict[str, str] = {}
        self._equates: dict[str, str] = {}

    def set_symbols(
        self,
        labels: dict[str, str],
        variables: dict[str, str],
        equates: dict[str, str],
    ) -> None:
        self._labels = dict(labels)
        self._variables = {f"_{name.lstrip('_')}": value for name, value in variables.items()}
        self._equates = {f"@{name.lstrip('@')}": value for name, value in equates.items()}
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        comment_start = text.find(";")
        raw_code = text if comment_start < 0 else text[:comment_start]
        code_start, code = code_without_label(raw_code)
        mnemonic = re.search(r"\S+", code)
        if invalid_instruction(code):
            self.setFormat(0, len(text), text_format("#FF8B96"))
            return
        if mnemonic:
            self.setFormat(
                code_start + mnemonic.start(),
                mnemonic.end() - mnemonic.start(),
                text_format(mnemonic_color(mnemonic.group())),
            )
        for match in REGISTER_TOKEN.finditer(code):
            if mnemonic and mnemonic.start() <= match.start() < mnemonic.end():
                continue
            self.setFormat(
                code_start + match.start(),
                match.end() - match.start(),
                text_format(register_color(match.group())),
            )
        for match in HEX_TOKEN.finditer(code):
            self.setFormat(
                code_start + match.start(),
                match.end() - match.start(),
                text_format("#7FD6A4"),
            )
        self._highlight_symbols(text, code, code_start)
        if comment_start >= 0:
            self.setFormat(comment_start, len(text) - comment_start, text_format("#7F879B"))

    def _highlight_symbols(self, original: str, code: str, code_start: int) -> None:
        for match in VARIABLE_TOKEN.finditer(code):
            if match.group() in self._variables:
                self.setFormat(
                    code_start + match.start(),
                    match.end() - match.start(),
                    text_format("#C084FC"),
                )
        for match in EQUATE_TOKEN.finditer(code):
            if match.group() in self._equates:
                self.setFormat(
                    code_start + match.start(),
                    match.end() - match.start(),
                    text_format("#FFB86C"),
                )
        for name in self._labels:
            for match in re.finditer(rf"\b{re.escape(name)}\b", original):
                self.setFormat(match.start(), match.end() - match.start(), text_format("#FFD166"))
