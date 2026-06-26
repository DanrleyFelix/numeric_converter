from __future__ import annotations

from src.modules.binary_workbench_constants import ASSEMBLY_LABEL_SEPARATOR as LABEL_SEPARATOR


def expand_pseudo_instructions(lines: list[str]) -> list[str]:
    expanded: list[str] = []
    for line in lines:
        expanded.extend(expand_pseudo_instruction(line))
    return expanded


def expand_pseudo_instruction(text: str) -> list[str]:
    normalized = _strip_comment(text).strip()
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
    if mnemonic == "move" and len(operands) == 2:
        return [f"addu {operands[0]}, {operands[1]}, $zero"]
    if mnemonic == "clear" and len(operands) == 1:
        return [f"addu {operands[0]}, $zero, $zero"]
    if mnemonic == "neg" and len(operands) == 2:
        return [f"subu {operands[0]}, $zero, {operands[1]}"]
    if mnemonic == "b" and len(operands) == 1:
        return [f"beq $zero, $zero, {operands[0]}"]
    return None


def _split_label(text: str) -> tuple[str | None, str]:
    if LABEL_SEPARATOR not in text:
        return None, text
    left, right = text.split(LABEL_SEPARATOR, 1)
    candidate = left.strip()
    if not candidate or " " in candidate or "\t" in candidate:
        return None, text
    return candidate, right.strip()


def _strip_comment(text: str) -> str:
    return text.split(";", 1)[0]
