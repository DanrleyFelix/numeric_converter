from __future__ import annotations

from src.core.binary_workbench.editor.commands.registers import (
    unique_stack_registers,
)

DEFAULT_STACK_REGISTERS = ("a0", "a1", "a2", "a3", "v0", "v1")
WORD_SIZE = 4


def stack_pointer_command(args: list[str]) -> list[str] | None:
    registers = list(DEFAULT_STACK_REGISTERS) if not args else unique_stack_registers(args)
    if not registers:
        return None
    size = len(registers) * WORD_SIZE
    return [
        f"addiu $sp, $sp, -{_hex(size)}",
        *_store_lines(registers),
        *_load_lines(registers),
        f"addiu $sp, $sp, {_hex(size)}",
    ]


def _store_lines(registers: list[str]) -> list[str]:
    return [
        f"sw ${register}, {_hex(index * WORD_SIZE)}($sp)"
        for index, register in enumerate(registers)
    ]


def _load_lines(registers: list[str]) -> list[str]:
    return [
        f"lw ${register}, {_hex(index * WORD_SIZE)}($sp)"
        for index, register in enumerate(registers)
    ]


def _hex(value: int) -> str:
    return f"0x{value:X}"
