from __future__ import annotations

LABEL_SEPARATOR = ":"
SHORT_IMMEDIATE_MIN = -0x8000
SHORT_IMMEDIATE_MAX = 0x7FFF
MIPS_WORD_MASK = 0xFFFFFFFF
MIPS_HALF_MASK = 0xFFFF
MIPS_HALF_SHIFT = 16


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
    if mnemonic == "li" and len(operands) == 2:
        return _expand_load_immediate(operands[0], operands[1])
    if mnemonic == "move" and len(operands) == 2:
        return [f"addu {operands[0]}, {operands[1]}, $zero"]
    if mnemonic == "clear" and len(operands) == 1:
        return [f"addu {operands[0]}, $zero, $zero"]
    if mnemonic == "neg" and len(operands) == 2:
        return [f"subu {operands[0]}, $zero, {operands[1]}"]
    if mnemonic == "b" and len(operands) == 1:
        return [f"beq $zero, $zero, {operands[0]}"]
    return None


def _expand_load_immediate(register: str, immediate: str) -> list[str]:
    value = _parse_int(immediate)
    if value is None or SHORT_IMMEDIATE_MIN <= value <= SHORT_IMMEDIATE_MAX:
        return [f"addiu {register}, $zero, {immediate}"]
    masked = value & MIPS_WORD_MASK
    upper = (masked >> MIPS_HALF_SHIFT) & MIPS_HALF_MASK
    lower = masked & MIPS_HALF_MASK
    lines = [f"lui {register}, 0x{upper:x}"]
    if lower:
        lines.append(f"ori {register}, {register}, 0x{lower:x}")
    return lines


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


def _parse_int(value: str) -> int | None:
    try:
        return int(value, 0)
    except ValueError:
        return None
