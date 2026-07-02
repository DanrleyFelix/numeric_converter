from __future__ import annotations

import re

from src.core.binary_workbench.mips_r3000a.constants import REGISTERS

AUTO_REGISTERS = ("t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9")
BRANCH_COMMANDS = {"blt", "ble", "bgt", "bge"}
LOAD_STORE_COMMANDS = {"lb", "lbu", "lh", "lhu", "lw", "sb", "sbu", "sh", "shu", "sw"}
STORE_ALIASES = {"sbu": "sb", "shu": "sh"}
OPERATORS = ("==", "!=", "<=", ">=", "<", ">")
COMMAND_NAMES = (
    "/sp", "/li", "/lb", "/lbu", "/lh", "/lhu", "/lw",
    "/sb", "/sbu", "/sh", "/shu", "/sw", "/blt", "/ble",
    "/bgt", "/bge", "/if", "/where",
)


def editor_command_names() -> tuple[str, ...]:
    return COMMAND_NAMES


def editor_command_output(name: str, args: list[str], where_index: int = 0) -> list[str] | None:
    if name == "li":
        return _li_command(args)
    if name in LOAD_STORE_COMMANDS:
        return _load_store_command(name, args)
    if name in BRANCH_COMMANDS:
        return _branch_command(name, args)
    if name == "if":
        return _if_command(args)
    if name == "where":
        return _where_command(args, where_index)
    return None


def _li_command(args: list[str]) -> list[str] | None:
    numbers, _, registers, _ = _split_args(args)
    if not numbers:
        return None
    register = registers[0] if registers else AUTO_REGISTERS[0]
    return _load_immediate_lines(register, numbers[0])


def _load_store_command(name: str, args: list[str]) -> list[str] | None:
    numbers, _, registers, _ = _split_args(args)
    if not numbers:
        return None
    offset = numbers[1] if len(numbers) > 1 else 0
    selected = _auto_registers(registers, 2)
    if selected is None:
        return None
    base, target = selected
    mnemonic = STORE_ALIASES.get(name, name)
    return [*_load_immediate_lines(base, numbers[0] - offset), f"{mnemonic} {target}, {_hex(offset)}({base})"]


def _branch_command(name: str, args: list[str]) -> list[str] | None:
    _, number_tokens, registers, others = _split_args(args)
    destination = others[0] if others else number_tokens[0] if number_tokens else None
    selected = _auto_registers(registers, 2)
    if destination is None or selected is None:
        return None
    return _comparison_branch_lines(name, selected[0], selected[1], destination)


def _if_command(args: list[str]) -> list[str] | None:
    parsed = _condition_with_destination(args)
    if parsed is None:
        return None
    return _condition_branch_lines(*parsed, branch_when_true=True)


def _where_command(args: list[str], index: int) -> list[str] | None:
    parsed = _condition_with_step(args)
    if parsed is None:
        return None
    r1, operator, r2, step = parsed
    start = f"where_{index + 1:03}_start"
    end = f"where_{index + 1:03}_end"
    condition = _condition_branch_lines(r1, operator, r2, end, False)
    return [
        f"{start}: {condition[0]}",
        *condition[1:],
        "# loop body stays here",
        f"addiu {r1}, {r1}, {_hex(step)}",
        f"beq zero, zero, {start}",
        "nop",
        f"{end}: nop",
    ]


def _condition_with_destination(args: list[str]) -> tuple[str, str, str, str] | None:
    parsed = _condition_args(args)
    if parsed is not None and len(args) >= 2:
        return (*parsed, args[1])
    if len(args) >= 4 and (r1 := _register(args[0])) and (r2 := _register(args[2])):
        return (r1, args[1], r2, args[3]) if args[1] in OPERATORS else None
    return None


def _condition_with_step(args: list[str]) -> tuple[str, str, str, int] | None:
    parsed = _condition_args(args)
    if parsed is not None and len(args) >= 2 and (step := _number(args[1])) is not None:
        return (*parsed, step)
    if len(args) >= 4 and (r1 := _register(args[0])) and (r2 := _register(args[2])):
        step = _number(args[3])
        return (r1, args[1], r2, step) if args[1] in OPERATORS and step is not None else None
    return None


def _condition_args(args: list[str]) -> tuple[str, str, str] | None:
    if not args:
        return None
    for operator in OPERATORS:
        if operator in args[0]:
            left, right = args[0].split(operator, 1)
            r1, r2 = _register(left), _register(right)
            return (r1, operator, r2) if r1 and r2 else None
    return None


def _comparison_branch_lines(command: str, r1: str, r2: str, destination: str) -> list[str]:
    operator = {"blt": "<", "ble": "<=", "bgt": ">", "bge": ">="}[command]
    return _condition_branch_lines(r1, operator, r2, destination, True)


def _condition_branch_lines(
    r1: str, operator: str, r2: str, destination: str, branch_when_true: bool
) -> list[str]:
    if operator in {"==", "!="}:
        branch = "beq" if (operator == "==") == branch_when_true else "bne"
        return [f"{branch} {r1}, {r2}, {destination}", "nop"]
    left, right = (r2, r1) if operator in {">", "<="} else (r1, r2)
    true_branch = "bne" if operator in {"<", ">"} else "beq"
    branch = true_branch if branch_when_true else ("beq" if true_branch == "bne" else "bne")
    return [f"slt t0, {left}, {right}", f"{branch} t0, zero, {destination}", "nop"]


def _load_immediate_lines(register: str, value: int) -> list[str]:
    value &= 0xFFFFFFFF
    return [
        f"lui {register}, {_hex((value >> 16) & 0xFFFF)}",
        f"ori {register}, {register}, {_hex(value & 0xFFFF)}",
    ]


def _auto_registers(registers: tuple[str, ...], count: int) -> tuple[str, ...] | None:
    values = list(registers)
    for register in AUTO_REGISTERS:
        if len(values) >= count:
            break
        if register not in values:
            values.append(register)
    return tuple(values[:count]) if len(values) >= count else None


def _split_args(args: list[str]) -> tuple[tuple[int, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    numbers: list[int] = []
    number_tokens: list[str] = []
    registers: list[str] = []
    others: list[str] = []
    for arg in args:
        if (number := _number(arg)) is not None:
            numbers.append(number)
            number_tokens.append(arg)
        elif (register := _register(arg)) is not None:
            registers.append(register)
        else:
            others.append(arg)
    return tuple(numbers), tuple(number_tokens), tuple(registers), tuple(others)


def _register(token: str) -> str | None:
    value = token.strip().lstrip("$").lower()
    return value if value and value in REGISTERS and not value.isdecimal() else None


def _number(token: str) -> int | None:
    if not re.fullmatch(r"-?(?:0x[0-9a-fA-F]+|\d+)", token.strip()):
        return None
    return int(token, 0)


def _hex(value: int) -> str:
    return f"-0x{abs(value):X}" if value < 0 else f"0x{value:X}"