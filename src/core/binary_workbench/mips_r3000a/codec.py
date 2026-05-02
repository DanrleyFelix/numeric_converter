from __future__ import annotations

from importlib import import_module

from src.modules.contracts import CPUArchCodec


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
        normalized = instruction.strip()
        if not normalized:
            return b"\x00\x00\x00\x00"
        if normalized.lower().startswith("word 0x"):
            return int(normalized.split("0x", 1)[1], 16).to_bytes(4, "little")
        if self._keystone is None:
            return None
        engine = self._keystone.Ks(
            self._keystone.KS_ARCH_MIPS,
            self._keystone.KS_MODE_MIPS32 + self._keystone.KS_MODE_LITTLE_ENDIAN,
        )
        encoded, _ = engine.asm(normalized, address)
        data = bytes(encoded[:4])
        return data if len(data) == 4 else None

    def disassemble(self, data: bytes, address: int) -> str:
        if len(data) != 4:
            return "word 0x00000000"
        if self._capstone is None:
            return f"word 0x{int.from_bytes(data, 'little'):08X}"
        engine = self._capstone.Cs(
            self._capstone.CS_ARCH_MIPS,
            self._capstone.CS_MODE_MIPS32 + self._capstone.CS_MODE_LITTLE_ENDIAN,
        )
        engine.detail = False
        result = next(engine.disasm(data, address), None)
        if result is None:
            return f"word 0x{int.from_bytes(data, 'little'):08X}"
        operands = f" {result.op_str}" if result.op_str else ""
        return f"{result.mnemonic}{operands}"

    def bytes_text(self, data: bytes) -> str:
        return " ".join(f"{value:02X}" for value in data)


def _module_exists(name: str) -> bool:
    try:
        import_module(name)
    except ModuleNotFoundError:
        return False
    return True
