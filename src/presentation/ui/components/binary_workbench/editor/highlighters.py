from __future__ import annotations

import re

from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

from src.core.binary_workbench.editor.commands.registry import is_editor_command_line
from src.core.binary_workbench.mips_r3000a.codec import (
    JUMP_NAVIGATION_BASE,
    JUMP_NAVIGATION_MNEMONICS,
    TWO_OPERAND_BRANCH_MNEMONICS,
)
from src.core.binary_workbench.mips_r3000a.comments import comment_start
from src.core.binary_workbench.mips_r3000a.constants import (
    BRANCH_OPCODES,
    MEMORY_OPERAND_ALIGNMENT,
    SPECIAL_BRANCH_RT,
)
from src.core.binary_workbench.mips_r3000a.preprocessor import expand_short_instruction
from src.core.binary_workbench.mips_r3000a.register_values import (
    effective_memory_address,
    known_register_values_after,
    register_state,
)
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.modules.constants import HEX_DIGIT_PATTERN
from src.presentation.ui.components.binary_workbench.editor.highlighter_colors import (
    psx_mips_highlight_color,
    psx_mips_required_highlight_color,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    BYTE_TOKEN,
    DECIMAL_TOKEN,
    EQUATE_TOKEN,
    HEX_TOKEN,
    REGISTER_TOKEN,
    VARIABLE_TOKEN,
    code_without_label,
    invalid_instruction,
    safe_int,
    text_format,
)

REFERENCE_OFFSET_PREFIX = "&"
JUMP_TARGET_TOKEN = re.compile(rf"&?(?:[@_]?[A-Za-z_][A-Za-z0-9_]*|[-+]?(?:0x{HEX_DIGIT_PATTERN}+|\d+))")
INSTRUCTION_TOKEN = re.compile(r"[^,\s]+")


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
        self._reference_offset_bases: dict[str, int] = {}
        self._jump_reference_offset = ""
        self._file_size = 0
        self._navigation_background_enabled = True
        self._known_register_values_by_block: dict[int, dict[int, int]] = {}

    def set_symbols(
        self,
        labels: dict[str, str],
        variables: dict[str, str],
        equates: dict[str, str],
    ) -> None:
        self._labels = {name.lower(): value for name, value in labels.items()}
        self._variables = {f"_{name.lstrip('_')}".lower(): value for name, value in variables.items()}
        self._equates = {f"@{name.lstrip('@')}".lower(): value for name, value in equates.items()}
        self._known_register_values_by_block.clear()
        self.rehighlight()

    def set_navigation_background_enabled(self, enabled: bool) -> None:
        self._navigation_background_enabled = enabled
        self.rehighlight()

    def set_jump_reference_offsets(
        self,
        reference_offset_bases: dict[str, str] | None,
        jump_reference_offset: str,
        file_size: int = 0,
    ) -> None:
        self._reference_offset_bases = {
            str(name): safe_int(str(value))
            for name, value in (reference_offset_bases or {}).items()
        }
        self._jump_reference_offset = (
            jump_reference_offset
            if jump_reference_offset in self._reference_offset_bases
            else ""
        )
        self._file_size = max(0, file_size)
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        block_number = self.currentBlock().blockNumber()
        register_values = (
            dict(self._known_register_values_by_block.get(block_number - 1, {0: 0}))
            if block_number > 0
            else {0: 0}
        )
        if is_editor_command_line(text):
            self.setFormat(0, len(text), text_format(psx_mips_required_highlight_color("command")))
            self._remember_register_values(block_number, register_values)
            return
        comment_start_index = comment_start(text)
        raw_code = text if comment_start_index < 0 else text[:comment_start_index]
        code_start, code = code_without_label(raw_code)
        mnemonic = re.search(r"\S+", code)
        if invalid_instruction(code):
            self.setFormat(0, len(text), text_format(psx_mips_required_highlight_color("invalid_instruction")))
        if mnemonic:
            mnemonic_color = psx_mips_highlight_color("mnemonic", mnemonic.group())
            if mnemonic_color is not None:
                self.setFormat(
                    code_start + mnemonic.start(),
                    mnemonic.end() - mnemonic.start(),
                    text_format(mnemonic_color),
                )
        for match in REGISTER_TOKEN.finditer(code):
            if mnemonic and mnemonic.start() <= match.start() < mnemonic.end():
                continue
            register_color = psx_mips_highlight_color("registers", match.group())
            if register_color is None:
                continue
            self.setFormat(
                code_start + match.start(),
                match.end() - match.start(),
                text_format(register_color),
            )
        for match in HEX_TOKEN.finditer(code):
            self.setFormat(
                code_start + match.start(),
                match.end() - match.start(),
                text_format(psx_mips_required_highlight_color("hex")),
            )
        for match in DECIMAL_TOKEN.finditer(code):
            if psx_mips_highlight_color("registers", match.group()) is not None:
                continue
            self.setFormat(
                code_start + match.start(),
                match.end() - match.start(),
                text_format(psx_mips_required_highlight_color("hex")),
            )
        self._highlight_symbols(text, code, code_start)
        if comment_start_index >= 0:
            self.setFormat(comment_start_index, len(text) - comment_start_index, text_format(psx_mips_required_highlight_color("comment")))
        invalid_target = self._invalid_jump_target_range(raw_code) if self._navigation_background_enabled else None
        if invalid_target is not None:
            self.setFormat(invalid_target[0], invalid_target[1] - invalid_target[0], invalid_address_format())
        invalid_memory = self._invalid_memory_alignment_range(raw_code, register_values)
        if invalid_memory is not None:
            self.setFormat(invalid_memory[0], invalid_memory[1] - invalid_memory[0], invalid_address_format())
        self._remember_register_values(
            block_number,
            known_register_values_after(expand_short_instruction(code), register_values),
        )

    def _highlight_symbols(self, original: str, code: str, code_start: int) -> None:
        for match in VARIABLE_TOKEN.finditer(code):
            if match.group().lower() in self._variables:
                self.setFormat(
                    code_start + match.start(),
                    match.end() - match.start(),
                    text_format(psx_mips_required_highlight_color("variable")),
                )
        for match in EQUATE_TOKEN.finditer(code):
            if match.group().lower() in self._equates:
                self.setFormat(
                    code_start + match.start(),
                    match.end() - match.start(),
                    text_format(psx_mips_required_highlight_color("equate")),
                )
        for name in self._labels:
            for match in re.finditer(rf"\b{re.escape(name)}\b", original, flags=re.IGNORECASE):
                style = text_format(psx_mips_required_highlight_color("label"))
                style.setFontWeight(QFont.Bold)
                self.setFormat(match.start(), match.end() - match.start(), style)

    def _invalid_jump_target_range(self, raw_code: str) -> tuple[int, int] | None:
        code_start, code = code_without_label(raw_code)
        tokens = [
            (match.group(), code_start + match.start(), code_start + match.end())
            for match in INSTRUCTION_TOKEN.finditer(code)
        ]
        if not tokens:
            return None
        mnemonic = tokens[0][0].lower()
        operand_index = _navigation_operand_index(mnemonic)
        if operand_index is None or len(tokens) <= operand_index:
            return None
        token, start, end = tokens[operand_index]
        if not JUMP_TARGET_TOKEN.fullmatch(token):
            return None
        target = self._target_file_offset(mnemonic, token)
        if (
            target is None
            or target < 0
            or target % ROW_BYTES != 0
            or (
                mnemonic not in JUMP_NAVIGATION_MNEMONICS
                and target >= self._file_size
            )
        ):
            return start, end
        return None

    def _target_file_offset(self, mnemonic: str, token: str) -> int | None:
        reference_token = token.startswith(REFERENCE_OFFSET_PREFIX)
        body = token[1:] if reference_token else token
        value = self._target_value(body)
        if value is None:
            return None
        if reference_token:
            if mnemonic not in JUMP_NAVIGATION_MNEMONICS or not self._jump_reference_offset:
                return None
            base = self._reference_offset_bases.get(self._jump_reference_offset, 0)
            return value - base
        normalized = body.lower()
        if normalized in self._labels:
            return value
        if mnemonic in JUMP_NAVIGATION_MNEMONICS and (
            normalized in self._variables
            or normalized in self._equates
            or self._numeric_token_value(body) is not None
        ):
            return value - JUMP_NAVIGATION_BASE if value >= JUMP_NAVIGATION_BASE else None
        return value

    def _invalid_memory_alignment_range(
        self,
        raw_code: str,
        register_values: dict[int, int] | None = None,
    ) -> tuple[int, int] | None:
        code_start, code = code_without_label(raw_code)
        tokens = [
            (match.group(), code_start + match.start(), code_start + match.end())
            for match in INSTRUCTION_TOKEN.finditer(code)
        ]
        if len(tokens) < 3:
            return None
        alignment = MEMORY_OPERAND_ALIGNMENT.get(tokens[0][0].lower())
        if alignment is None:
            return None
        token, start, end = tokens[2]
        address = self._memory_operand_address(token, register_values or {0: 0})
        return (start, end) if address is not None and address % alignment != 0 else None

    def _memory_operand_address(self, token: str, register_values: dict[int, int]) -> int | None:
        expanded = self._symbol_value(token) or token
        if "(" not in expanded:
            return None
        immediate = expanded.split("(", 1)[0].strip()
        if immediate:
            resolved = self._symbol_value(immediate)
            if resolved is not None:
                expanded = f"{resolved.split('(', 1)[0]}({expanded.split('(', 1)[1]}"
        return effective_memory_address(expanded, register_values)

    def _symbol_value(self, token: str) -> str | None:
        normalized = token.lower()
        for symbols in (self._labels, self._variables, self._equates):
            if normalized in symbols:
                return str(symbols[normalized])
        return None

    def _remember_register_values(self, block_number: int, values: dict[int, int]) -> None:
        self._known_register_values_by_block[block_number] = values
        self.setCurrentBlockState(register_state(values))

    def _target_value(self, token: str) -> int | None:
        normalized = token.lower()
        for symbols in (self._labels, self._variables, self._equates):
            if normalized in symbols:
                return safe_int(symbols[normalized], -1)
        return self._numeric_token_value(token)

    def _numeric_token_value(self, token: str) -> int | None:
        try:
            return int(token, 0)
        except ValueError:
            return None



def invalid_address_format() -> QTextCharFormat:
    style = QTextCharFormat()
    style.setBackground(QColor(psx_mips_required_highlight_color("invalid_instruction")))
    return style


def _navigation_operand_index(mnemonic: str) -> int | None:
    if mnemonic in JUMP_NAVIGATION_MNEMONICS:
        return 1
    if mnemonic in TWO_OPERAND_BRANCH_MNEMONICS:
        return 2
    if mnemonic in {*BRANCH_OPCODES, *SPECIAL_BRANCH_RT}:
        return 3
    return None
