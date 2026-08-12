from __future__ import annotations

from src.modules.binary_workbench_constants import ASSEMBLY_LABEL_SEPARATOR as LABEL_SEPARATOR
from src.core.binary_workbench.mips_r3000a.comments import strip_comment

LI_IMMEDIATE_MIN = -0x8000
LI_IMMEDIATE_MAX = 0xFFFF
PSEUDO_INSTRUCTION_MNEMONICS = frozenset({"b", "clear", "li", "move", "neg", "negu"})


def expand_pseudo_instructions(lines: list[str]) -> list[str]:
    expanded: list[str] = []
    for line in lines:
        expanded.extend(expand_pseudo_instruction(line))
    return expanded


def expand_pseudo_instruction(text: str) -> list[str]:
    normalized = strip_comment(text).strip()
    if not normalized:
        return [text]
    label, code = _split_label(normalized)
    expanded = _expand_code(code)
    if expanded is None:
        return [text]
    if label and expanded:
        expanded[0] = f"{label}: {expanded[0]}"
    return expanded


def _expand_code(code: str) -> list[str] | None:
    parts = code.replace(",", " ").split()
    if not parts:
        return None
    mnemonic = parts[0].lower()
    operands = parts[1:]
    if mnemonic == "li" and len(operands) == 2:
        return _expand_li(operands)
    if mnemonic == "move" and len(operands) == 2:
        return [f"addu {operands[0]}, {operands[1]}, $zero"]
    if mnemonic == "clear" and len(operands) == 1:
        return [f"addu {operands[0]}, $zero, $zero"]
    if mnemonic == "neg" and len(operands) == 2:
        return [f"sub {operands[0]}, $zero, {operands[1]}"]
    if mnemonic == "negu" and len(operands) == 2:
        return [f"subu {operands[0]}, $zero, {operands[1]}"]
    if mnemonic == "b" and len(operands) == 1:
        return [f"beq $zero, $zero, {operands[0]}"]
    return None


def _expand_li(operands: list[str]) -> list[str] | None:
    try:
        value = int(operands[1], 0)
    except ValueError:
        return None
    if LI_IMMEDIATE_MIN <= value <= LI_IMMEDIATE_MAX:
        return [f"addiu {operands[0]}, $zero, {operands[1]}"]
    return None


def _split_label(text: str) -> tuple[str | None, str]:
    if LABEL_SEPARATOR not in text:
        return None, text
    left, right = text.split(LABEL_SEPARATOR, 1)
    candidate = left.strip()
    if not candidate or left != left.rstrip() or " " in candidate or "\t" in candidate:
        return None, text
    return candidate, right.strip()
