import re

from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QToolTip

from src.core.binary_workbench.mips_r3000a.codec import (
    JUMP_NAVIGATION_MNEMONICS,
    TWO_OPERAND_BRANCH_MNEMONICS,
)
from src.core.binary_workbench.mips_r3000a.constants import BRANCH_OPCODES
from src.core.binary_workbench.mips_r3000a.preprocessor import ZERO_BRANCH_PSEUDOS
from src.modules.constants import HEX_DIGIT_PATTERN
from src.modules.contracts import CPUArchCodec
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    COMPLETION_TOKEN,
    safe_int,
)

REFERENCE_OFFSET_PREFIX = "&"
JUMP_TARGET_TOKEN = re.compile(rf"&?(?:[@_]?[A-Za-z_][A-Za-z0-9_]*|[-+]?(?:0x{HEX_DIGIT_PATTERN}+|\d+))")
JUMP_MNEMONICS = {"j", "jump", "jal"}
LABEL_NAVIGATION_MNEMONICS = {
    *JUMP_NAVIGATION_MNEMONICS,
    *TWO_OPERAND_BRANCH_MNEMONICS,
    *BRANCH_OPCODES,
    *ZERO_BRANCH_PSEUDOS,
    "b",
}
BRANCH_IMMEDIATE_MIN = -0x8000
BRANCH_IMMEDIATE_MAX = 0x7FFF
DEFAULT_ROW_BYTES = 4


class EditorLabelNavigationMixin:
    def set_label_target_resolver(
        self,
        resolver: Callable[[str], int | None],
    ) -> None:
        """Set the on-demand resolver used for clicked label operands."""

        self._label_target_resolver = resolver

    def set_label_offsets(self, labels: dict[str, str]) -> None:
        self._label_offsets = {
            name.lower(): (name, safe_int(offset))
            for name, offset in labels.items()
        }

    def set_jump_navigation(
        self,
        codec: CPUArchCodec,
        labels: dict[str, str],
        variables: dict[str, str],
        equates: dict[str, str],
        reference_offset_bases: dict[str, str] | None = None,
        visible_reference_offsets: list[str] | None = None,
        jump_reference_offset: str = "",
        navigation_start_offset: int = 0,
        row_bytes: int = DEFAULT_ROW_BYTES,
    ) -> None:
        self._jump_codec = codec
        label_symbols = {name.lower(): value for name, value in labels.items()}
        self._jump_label_symbols = set(label_symbols)
        variable_symbols = {f"_{name.lstrip('_')}".lower(): value for name, value in variables.items()}
        equate_symbols = {f"@{name.lstrip('@')}".lower(): value for name, value in equates.items()}
        self._jump_symbols = {**label_symbols, **variable_symbols, **equate_symbols}
        self._jump_reference_offset = jump_reference_offset
        self._jump_reference_bases = {
            str(name): safe_int(str(value))
            for name, value in (reference_offset_bases or {}).items()
        }
        self._jump_visible_reference_offsets = list(visible_reference_offsets or [])
        self._jump_navigation_start_offset = max(0, navigation_start_offset)
        self._jump_navigation_row_bytes = max(1, row_bytes)

    def _label_at_position(self, position: QPoint) -> tuple[str, int] | None:
        return self._label_offsets.get(self._strict_token_at_position(position).lower())

    def _jump_target_at_position(self, position: QPoint) -> int | None:
        details = self._jump_target_details_at_position(position)
        return details[0] if details is not None else None

    def _jump_target_details_at_position(self, position: QPoint) -> tuple[int, str] | None:
        token = self._strict_token_at_position(position, JUMP_TARGET_TOKEN)
        if not token or self._jump_codec is None:
            return None
        if self._label_declaration_at_position(position):
            return None
        mnemonic = self._mnemonic_at_position(position)
        if token.lower() in self._jump_label_symbols and mnemonic not in LABEL_NAVIGATION_MNEMONICS:
            return None
        if token.startswith(REFERENCE_OFFSET_PREFIX):
            target = self._reference_target(token, mnemonic)
        else:
            target = self._standard_target(position, token)
        if target is None:
            return None
        return target, self._jump_target_tooltip(target)

    def _standard_target(self, position: QPoint, token: str) -> int | None:
        if self._label_target_resolver is not None:
            live_target = self._label_target_resolver(token)
            if live_target is not None:
                return live_target
            if token.lower() in self._jump_label_symbols:
                return None
        instruction = self.cursorForPosition(position).block().text()
        return self._jump_codec.jump_navigation_target(
            instruction,
            token,
            self._jump_symbols,
        )

    def _reference_target(self, token: str, mnemonic: str) -> int | None:
        if mnemonic not in JUMP_MNEMONICS or not self._jump_reference_offset:
            return None
        value = self._token_value(token[1:])
        if value is None:
            return None
        base = self._jump_reference_bases.get(self._jump_reference_offset, 0)
        return value - base

    def _token_value(self, token: str) -> int | None:
        normalized = token.lower()
        if normalized in self._jump_symbols:
            return self._jump_symbol_value(normalized)
        return self._numeric_token_value(token)

    def _jump_symbol_value(self, token: str) -> int | None:
        try:
            return int(self._jump_symbols[token], 0)
        except (KeyError, ValueError):
            return None

    def _numeric_token_value(self, token: str) -> int | None:
        try:
            return int(token, 0)
        except ValueError:
            return None

    def _jump_target_tooltip(self, target: int) -> str:
        parts = [f"{BINARY_WORKBENCH_TEXT.FILE_OFFSET}: {_offset_text(target)}"]
        for name in self._jump_visible_reference_offsets:
            if name == BINARY_WORKBENCH_TEXT.FILE:
                continue
            base = self._jump_reference_bases.get(name, 0)
            value = target + base
            if value <= 0 or base <= 0:
                continue
            parts.append(f"{name}: 0x{value:08X}")
        return " | ".join(parts)

    def _navigation_target_at_position(self, position: QPoint) -> int | None:
        return self._jump_target_at_position(position)

    def _navigation_warning_at_position(self, position: QPoint) -> str:
        if self._invalid_reference_marker_at_position(position):
            return BINARY_WORKBENCH_TEXT.STATUS_OFFSET_OUT_OF_RANGE
        details = self._jump_target_details_at_position(position)
        if details is None:
            return ""
        if details[0] % self._jump_navigation_row_bytes != 0:
            return BINARY_WORKBENCH_TEXT.STATUS_TARGET_MISALIGNED
        if not self._branch_target_in_range(position, details[0]):
            return BINARY_WORKBENCH_TEXT.STATUS_BRANCH_OUT_OF_RANGE
        return ""

    def _invalid_reference_marker_at_position(self, position: QPoint) -> bool:
        token = self._strict_token_at_position(position, JUMP_TARGET_TOKEN)
        if not token.startswith(REFERENCE_OFFSET_PREFIX):
            return False
        return self._mnemonic_at_position(position) not in JUMP_MNEMONICS or not self._jump_reference_offset

    def _branch_target_in_range(self, position: QPoint, target: int) -> bool:
        if self._mnemonic_at_position(position) in JUMP_MNEMONICS:
            return True
        row_bytes = self._jump_navigation_row_bytes
        source = self._navigation_source_offset(position)
        delta = target - (source + row_bytes)
        if delta % row_bytes != 0:
            return False
        immediate = delta // row_bytes
        return BRANCH_IMMEDIATE_MIN <= immediate <= BRANCH_IMMEDIATE_MAX

    def _navigation_source_offset(self, position: QPoint) -> int:
        return self._jump_navigation_start_offset + (self.cursorForPosition(position).blockNumber() * self._jump_navigation_row_bytes)

    def _mnemonic_at_position(self, position: QPoint) -> str:
        block_text = self.cursorForPosition(position).block().text()
        code = block_text.split(";", 1)[0].split("#", 1)[0].split("//", 1)[0]
        if ":" in code:
            code = code.split(":", 1)[1]
        parts = code.replace(",", " ").split()
        return parts[0].lower() if parts else ""

    def _label_declaration_at_position(self, position: QPoint) -> bool:
        cursor = self.cursorForPosition(position)
        code = cursor.block().text().split(";", 1)[0].split("#", 1)[0].split("//", 1)[0]
        colon = code.find(":")
        return colon >= 0 and cursor.positionInBlock() <= colon

    def _strict_token_at_position(
        self,
        position: QPoint,
        pattern: re.Pattern[str] = COMPLETION_TOKEN,
    ) -> str:
        block = self.cursorForPosition(position).block()
        for match in pattern.finditer(block.text()):
            if self._token_contains_x(block, match.start(), match.end(), position.x()):
                return match.group()
        return ""

    def _token_contains_x(self, block, start: int, end: int, x: int) -> bool:
        cursor = QTextCursor(block)
        set_cursor_position(cursor, block.position() + start)
        left = self.cursorRect(cursor).left()
        set_cursor_position(cursor, block.position() + end)
        right = self.cursorRect(cursor).left()
        margin = BINARY_WORKBENCH_LAYOUT.EDITOR_LABEL_CLICK_MARGIN
        return left - margin <= x <= right + margin

    def _update_label_cursor(self, position: QPoint) -> None:
        details = self._jump_target_details_at_position(position)
        if details is not None:
            self.viewport().setCursor(Qt.PointingHandCursor)
            QToolTip.showText(self.viewport().mapToGlobal(position), details[1], self.viewport())
            return
        symbol = self._symbol_token_at_position(position)
        if symbol:
            self.viewport().setCursor(Qt.PointingHandCursor)
            QToolTip.showText(
                self.viewport().mapToGlobal(position),
                self._symbol_tooltips[symbol],
                self.viewport(),
            )
            return
        QToolTip.hideText()
        self.viewport().setCursor(Qt.IBeamCursor)

    def mousePressEvent(self, event) -> None:
        position = event.position().toPoint()
        self._pressed_navigation_target = self._navigation_target_at_position(position)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._stop_selection_scroll()
        super().mouseReleaseEvent(event)
        position = event.position().toPoint()
        edit_jump_symbol = (
            event.button() == Qt.LeftButton
            and bool(event.modifiers() & Qt.ControlModifier)
            and bool(self._symbol_token_at_position(position))
        )
        if edit_jump_symbol:
            self._pressed_navigation_target = None
            return
        warning = self._navigation_warning_at_position(position)
        if event.button() == Qt.LeftButton and warning:
            self.navigationWarningRequested.emit(warning)
            self._pressed_navigation_target = None
            return
        target = self._navigation_target_at_position(position)
        if event.button() == Qt.LeftButton and target is not None and target == self._pressed_navigation_target:
            self.jumpNavigationActivated.emit(target, self._navigation_source_offset(position))
        if event.button() == Qt.LeftButton:
            self._show_symbol_tooltip(event)
        self._pressed_navigation_target = None


def _offset_text(value: int) -> str:
    if value < 0:
        return f"-0x{abs(value):08X}"
    return f"0x{value:08X}"
