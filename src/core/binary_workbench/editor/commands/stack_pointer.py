from __future__ import annotations

from src.core.binary_workbench.editor.commands.registers import (
    unique_stack_registers,
)

DEFAULT_STACK_REGISTERS = ("a0", "a1", "a2", "a3", "v0", "v1")
REGISTER_GROUPS = {
    "s": ("s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7"),
    "t": ("t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9"),
    "a": ("a0", "a1", "a2", "a3"),
    "v": ("v0", "v1"),
    "k": ("k0", "k1"),
}
WORD_SIZE = 4


def stack_pointer_command(args: list[str]) -> list[str] | None:
    registers = list(DEFAULT_STACK_REGISTERS) if not args else _stack_registers(args)
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


def _stack_registers(args: list[str]) -> list[str] | None:
    expanded: list[str] = []
    for arg in args:
        value = arg.strip().lstrip("$").lower()
        values = REGISTER_GROUPS.get(value, (arg,))
        expanded.extend(values)
    return unique_stack_registers(expanded)


def _hex(value: int) -> str:
    return f"0x{value:X}"