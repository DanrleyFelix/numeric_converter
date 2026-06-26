from __future__ import annotations

import re

from src.core.binary_workbench.mips_r3000a.constants import REGISTERS

REPLACEABLE_REGISTER = re.compile(
    r"(?<![A-Za-z0-9_])\$?(?:a[0-3]|s[0-8]|t[0-9]|v[0-1])(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
STACK_REGISTER_NAMES = set(REGISTERS) - {"zero", "sp"}


def normalize_stack_register(token: str) -> str | None:
    value = token.strip().lstrip("$").lower()
    return value if value in STACK_REGISTER_NAMES else None


def normalize_replaceable_register(token: str) -> str | None:
    value = token.strip().lstrip("$").lower()
    if REPLACEABLE_REGISTER.fullmatch(value):
        return value
    if REPLACEABLE_REGISTER.fullmatch(f"${value}"):
        return value
    return None


def unique_stack_registers(tokens: list[str]) -> list[str] | None:
    values: list[str] = []
    for token in tokens:
        register = normalize_stack_register(token)
        if register is None:
            return None
        if register not in values:
            values.append(register)
    return values


def replaceable_register_order(lines: list[str]) -> list[str]:
    values: list[str] = []
    for line in lines:
        for match in REPLACEABLE_REGISTER.finditer(line):
            register = normalize_replaceable_register(match.group())
            if register is not None and register not in values:
                values.append(register)
    return values


def replace_registers_in_lines(lines: list[str], args: list[str]) -> list[str]:
    replacements = [
        register
        for arg in args
        if (register := normalize_replaceable_register(arg)) is not None
    ]
    if not replacements:
        return list(lines)
    targets = replaceable_register_order(lines)
    mapping = {
        target: replacement
        for target, replacement in zip(targets, replacements)
    }
    if not mapping:
        return list(lines)
    return [REPLACEABLE_REGISTER.sub(lambda match: _substitute(match, mapping), line) for line in lines]


def _substitute(match: re.Match[str], mapping: dict[str, str]) -> str:
    current = normalize_replaceable_register(match.group())
    if current is None or current not in mapping:
        return match.group()
    prefix = "$" if match.group().startswith("$") else ""
    return f"{prefix}{mapping[current]}"
