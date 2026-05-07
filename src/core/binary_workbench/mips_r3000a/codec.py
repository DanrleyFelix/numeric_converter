from __future__ import annotations

from importlib import import_module

from src.modules.contracts import CPUArchCodec

_REGISTERS = {
    "zero": 0, "at": 1, "v0": 2, "v1": 3, "a0": 4, "a1": 5, "a2": 6, "a3": 7,
    "t0": 8, "t1": 9, "t2": 10, "t3": 11, "t4": 12, "t5": 13, "t6": 14, "t7": 15,
    "s0": 16, "s1": 17, "s2": 18, "s3": 19, "s4": 20, "s5": 21, "s6": 22, "s7": 23,
    "t8": 24, "t9": 25, "k0": 26, "k1": 27, "gp": 28, "sp": 29, "fp": 30, "s8": 30, "ra": 31,
}
_REGISTER_NAMES = {value: name for name, value in _REGISTERS.items() if name != "s8"}
_I_OPCODES = {"addiu": 0x09, "ori": 0x0D, "lui": 0x0F, "lw": 0x23, "sw": 0x2B, "lh": 0x21, "lhu": 0x25, "sh": 0x29, "lb": 0x20, "lbu": 0x24, "sb": 0x28}
_I_OPCODES["sltiu"] = 0x0B
_BRANCH_OPCODES = {"beq": 0x04, "bne": 0x05, "blez": 0x06, "bgtz": 0x07}
_SPECIAL_BRANCH_RT = {"bltz": 0x00, "bgez": 0x01}
_J_OPCODES = {"j": 0x02, "jal": 0x03}
_R_FUNCTS = {"add": 0x20, "addu": 0x21, "subu": 0x23}


class PsxMipsR3000ACodec(CPUArchCodec):
    def __init__(self) -> None:
        self._capstone = import_module("capstone") if _module_exists("capstone") else None
        self._keystone = import_module("keystone") if _module_exists("keystone") else None

    @property
    def display_name(self) -> str:
        return "PSX - Mips R3000A"

    @property
    def word_size(self) -> int:
        return 4

    @property
    def default_reference_offsets(self) -> tuple[str, ...]:
        return ("File", "RAM", "SLUS")

    def assemble(self, instruction: str, address: int) -> bytes | None:
        normalized = _strip_comment(instruction).strip()
        if not normalized:
            return b"\x00\x00\x00\x00"
        if normalized.lower() == "nop":
            return b"\x00\x00\x00\x00"
        if normalized.lower().startswith(("word 0x", ".word 0x")):
            try:
                return int(normalized.split("0x", 1)[1], 16).to_bytes(4, "little")
            except ValueError:
                return None
        if self._keystone is not None:
            try:
                engine = self._keystone.Ks(self._keystone.KS_ARCH_MIPS, self._keystone.KS_MODE_MIPS32 + self._keystone.KS_MODE_LITTLE_ENDIAN)
                encoded, _ = engine.asm(normalized, address)
                data = bytes(encoded[:4])
                if len(data) == 4:
                    return data
            except Exception:
                pass
        try:
            return _assemble_fallback(normalized, address)
        except Exception:
            return None

    def disassemble(self, data: bytes, address: int) -> str:
        if len(data) != 4:
            return "word 0x00000000"
        if self._capstone is not None:
            engine = self._capstone.Cs(self._capstone.CS_ARCH_MIPS, self._capstone.CS_MODE_MIPS32 + self._capstone.CS_MODE_LITTLE_ENDIAN)
            engine.detail = False
            result = next(engine.disasm(data, address), None)
            if result is not None:
                operands = f" {result.op_str}" if result.op_str else ""
                return f"{result.mnemonic}{operands}"
        return _disassemble_fallback(int.from_bytes(data, "little"), address)

    def bytes_text(self, data: bytes) -> str:
        return " ".join(f"{value:02X}" for value in data)


def _assemble_fallback(instruction: str, address: int) -> bytes | None:
    parts = instruction.replace(",", " ").split()
    mnemonic = parts[0].lower()
    operands = parts[1:]
    if mnemonic in _J_OPCODES and operands:
        return _j_type(_J_OPCODES[mnemonic], _number(operands[0]) >> 2)
    if mnemonic == "jr" and operands:
        return _r_type(_register(operands[0]), 0, 0, 0, 0x08)
    if mnemonic == "jalr" and operands:
        rs = _register(operands[0])
        rd = _register(operands[1]) if len(operands) > 1 else 31
        return _r_type(rs, 0, rd, 0, 0x09)
    if mnemonic in _R_FUNCTS:
        rd, rs, rt = _register(operands[0]), _register(operands[1]), _register(operands[2])
        return _r_type(rs, rt, rd, 0, _R_FUNCTS[mnemonic])
    if mnemonic in _I_OPCODES:
        return _assemble_i_type(mnemonic, operands)
    if mnemonic in _BRANCH_OPCODES:
        return _assemble_branch(mnemonic, operands, address)
    if mnemonic in _SPECIAL_BRANCH_RT:
        offset = ((_number(operands[1]) - (address + 4)) >> 2) & 0xFFFF
        word = (0x01 << 26) | (_register(operands[0]) << 21) | (_SPECIAL_BRANCH_RT[mnemonic] << 16) | offset
        return word.to_bytes(4, "little")
    return None


def _assemble_i_type(mnemonic: str, operands: list[str]) -> bytes | None:
    opcode = _I_OPCODES[mnemonic]
    if mnemonic == "lui":
        rt, immediate = _register(operands[0]), _number(operands[1]) & 0xFFFF
        word = (opcode << 26) | (rt << 16) | immediate
        return word.to_bytes(4, "little")
    if mnemonic in {"lw", "sw", "lh", "lhu", "sh", "lb", "lbu", "sb"}:
        rt = _register(operands[0])
        immediate, base = _offset_operand(operands[1])
        word = (opcode << 26) | (base << 21) | (rt << 16) | (immediate & 0xFFFF)
        return word.to_bytes(4, "little")
    rt, rs, immediate = _register(operands[0]), _register(operands[1]), _number(operands[2])
    word = (opcode << 26) | (rs << 21) | (rt << 16) | (immediate & 0xFFFF)
    return word.to_bytes(4, "little")


def _assemble_branch(mnemonic: str, operands: list[str], address: int) -> bytes:
    opcode = _BRANCH_OPCODES[mnemonic]
    if mnemonic in {"blez", "bgtz"}:
        rs, offset = _register(operands[0]), ((_number(operands[1]) - (address + 4)) >> 2) & 0xFFFF
        word = (opcode << 26) | (rs << 21) | offset
        return word.to_bytes(4, "little")
    rs, rt = _register(operands[0]), _register(operands[1])
    offset = ((_number(operands[2]) - (address + 4)) >> 2) & 0xFFFF
    word = (opcode << 26) | (rs << 21) | (rt << 16) | offset
    return word.to_bytes(4, "little")


def _disassemble_fallback(word: int, address: int) -> str:
    if word == 0:
        return "nop"
    opcode = (word >> 26) & 0x3F
    if opcode in {0x02, 0x03}:
        mnemonic = "jal" if opcode == 0x03 else "j"
        return f"{mnemonic} 0x{((word & 0x03FFFFFF) << 2):X}"
    if opcode == 0x00:
        rs, rt, rd, funct = (word >> 21) & 0x1F, (word >> 16) & 0x1F, (word >> 11) & 0x1F, word & 0x3F
        if funct == 0x08:
            return f"jr ${_REGISTER_NAMES.get(rs, 'zero')}"
        if funct == 0x09:
            return f"jalr ${_REGISTER_NAMES.get(rs, 'zero')}, ${_REGISTER_NAMES.get(rd, 'ra')}"
        mnemonic = _mnemonic_from_funct(funct)
        if mnemonic is not None:
            return f"{mnemonic} ${_REGISTER_NAMES.get(rd, 'zero')}, ${_REGISTER_NAMES.get(rs, 'zero')}, ${_REGISTER_NAMES.get(rt, 'zero')}"
    if opcode in _I_OPCODES.values():
        return _disassemble_i_type(opcode, word)
    if opcode in _BRANCH_OPCODES.values() or opcode == 0x01:
        return _disassemble_branch(opcode, word, address)
    return f"word 0x{word:08X}"


def _disassemble_i_type(opcode: int, word: int) -> str:
    rs, rt, imm = (word >> 21) & 0x1F, (word >> 16) & 0x1F, _signed16(word & 0xFFFF)
    registers = (_REGISTER_NAMES.get(rt, "zero"), _REGISTER_NAMES.get(rs, "zero"))
    if opcode == 0x0F:
        return f"lui ${registers[0]}, 0x{word & 0xFFFF:04X}"
    if opcode in {0x23, 0x2B, 0x21, 0x25, 0x29, 0x20, 0x24, 0x28}:
        return f"{_mnemonic_from_opcode(opcode)} ${registers[0]}, {_hex_or_signed(imm)}(${registers[1]})"
    return f"{_mnemonic_from_opcode(opcode)} ${registers[0]}, ${registers[1]}, {_hex_or_signed(imm)}"


def _disassemble_branch(opcode: int, word: int, address: int) -> str:
    rs, rt, imm = (word >> 21) & 0x1F, (word >> 16) & 0x1F, _signed16(word & 0xFFFF)
    target = address + 4 + (imm << 2)
    if opcode == 0x01:
        mnemonic = "bgez" if rt == 0x01 else "bltz"
        return f"{mnemonic} ${_REGISTER_NAMES.get(rs, 'zero')}, 0x{target:X}"
    if opcode in {0x06, 0x07}:
        return f"{_mnemonic_from_opcode(opcode)} ${_REGISTER_NAMES.get(rs, 'zero')}, 0x{target:X}"
    return f"{_mnemonic_from_opcode(opcode)} ${_REGISTER_NAMES.get(rs, 'zero')}, ${_REGISTER_NAMES.get(rt, 'zero')}, 0x{target:X}"


def _mnemonic_from_opcode(opcode: int) -> str:
    mapping = {value: key for key, value in _I_OPCODES.items()}
    mapping.update({value: key for key, value in _BRANCH_OPCODES.items()})
    return mapping.get(opcode, "word")


def _mnemonic_from_funct(funct: int) -> str | None:
    mapping = {value: key for key, value in _R_FUNCTS.items()}
    return mapping.get(funct)


def _register(token: str) -> int:
    return _REGISTERS[token.lstrip("$").lower()]


def _number(token: str) -> int:
    return int(token, 16) if token.lower().startswith(("0x", "-0x")) else int(token, 10)


def _offset_operand(token: str) -> tuple[int, int]:
    immediate, base = token.split("(", 1)
    return _number(immediate), _register(base.rstrip(")"))


def _r_type(rs: int, rt: int, rd: int, shamt: int, funct: int) -> bytes:
    word = (rs << 21) | (rt << 16) | (rd << 11) | (shamt << 6) | funct
    return word.to_bytes(4, "little")


def _j_type(opcode: int, target: int) -> bytes:
    return ((opcode << 26) | (target & 0x03FFFFFF)).to_bytes(4, "little")


def _signed16(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


def _hex_or_signed(value: int) -> str:
    return f"-0x{abs(value):X}" if value < 0 else f"0x{value:X}"


def _module_exists(name: str) -> bool:
    try:
        import_module(name)
    except ModuleNotFoundError:
        return False
    return True


def _strip_comment(text: str) -> str:
    return text.split(";", 1)[0]
