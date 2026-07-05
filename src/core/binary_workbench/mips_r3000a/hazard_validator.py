from __future__ import annotations

import re
from dataclasses import dataclass

from src.core.binary_workbench.mips_r3000a.constants import (
    BRANCH_OPCODES,
    J_OPCODES,
    R_JUMP_FUNCTS,
    REGISTERS,
)

LOAD_MNEMONICS = {"lb", "lbu", "lh", "lhu", "lw", "lwl", "lwr"}
STORE_MNEMONICS = {"sb", "sh", "sw", "swl", "swr"}
JUMP_MNEMONICS = {*BRANCH_OPCODES, *J_OPCODES, *R_JUMP_FUNCTS, "bgez", "bltz"}
REGISTER_PATTERN = re.compile(
    r"\$(r?\d+|[a-z][a-z0-9]*)|(?<![0-9a-z])([a-z][a-z0-9]*)(?![0-9a-z])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MipsHazard:
    line_index: int
    severity: str
    message: str


def validate_mips_hazards(instructions: list[str]) -> list[MipsHazard]:
    hazards: list[MipsHazard] = []
    pending_load: str | None = None
    previous_jump = False
    for index, instruction in enumerate(instructions):
        mnemonic, operands = _parts(instruction)
        if not mnemonic:
            continue
        if pending_load and pending_load in _read_registers(mnemonic, operands):
            hazards.append(
                MipsHazard(
                    index,
                    "warning",
                    f"Possibly Hazard: ${pending_load} may be used before load is ready.",
                )
            )
        if previous_jump and mnemonic in JUMP_MNEMONICS:
            hazards.append(
                MipsHazard(
                    index,
                    "error",
                    "Hazard!: consecutive jump/branch instructions.",
                )
            )
        pending_load = _load_target(mnemonic, operands)
        previous_jump = mnemonic in JUMP_MNEMONICS
    return hazards


def _parts(instruction: str) -> tuple[str, list[str]]:
    tokens = instruction.replace(",", " ").split()
    if not tokens:
        return "", []
    return tokens[0].lower(), tokens[1:]


def _load_target(mnemonic: str, operands: list[str]) -> str | None:
    if mnemonic not in LOAD_MNEMONICS or not operands:
        return None
    return _register_name(operands[0])


def _read_registers(mnemonic: str, operands: list[str]) -> set[str]:
    if mnemonic in LOAD_MNEMONICS:
        return _registers_from_text(" ".join(operands[1:]))
    if mnemonic in STORE_MNEMONICS:
        return _registers_from_text(" ".join(operands))
    if mnemonic in JUMP_MNEMONICS:
        return _registers_from_text(" ".join(operands))
    if len(operands) >= 3:
        return _registers_from_text(" ".join(operands[1:]))
    return _registers_from_text(" ".join(operands))


def _registers_from_text(text: str) -> set[str]:
    return {
        register
        for match in REGISTER_PATTERN.finditer(text)
        if (register := _canonical_register(_match_register(match)))
    }


def _register_name(token: str) -> str:
    match = REGISTER_PATTERN.search(token)
    return _canonical_register(_match_register(match)) if match else ""


def _match_register(match) -> str:
    return next(group for group in match.groups() if group)


def _canonical_register(name: str) -> str:
    raw = name.lower()
    index = REGISTERS.get(raw)
    if index is None:
        return raw
    return str(index)
