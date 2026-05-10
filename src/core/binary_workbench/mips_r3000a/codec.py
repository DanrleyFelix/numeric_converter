from __future__ import annotations

from importlib import import_module

from src.core.binary_workbench.mips_r3000a.assembler import assemble_fallback
from src.core.binary_workbench.mips_r3000a.disassembler import disassemble_fallback
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
        normalized = _strip_comment(instruction).strip()
        if not normalized:
            return b"\x00\x00\x00\x00"
        if normalized.lower() == "nop":
            return b"\x00\x00\x00\x00"
        lower = normalized.lower()
        if lower.startswith(("word 0x", ".word 0x")):
            try:
                hex_start = lower.index("0x") + 2
                return int(normalized[hex_start:], 16).to_bytes(4, "little")
            except (ValueError, IndexError):
                return None
        if self._keystone is not None:
            try:
                engine = self._keystone.Ks(
                    self._keystone.KS_ARCH_MIPS,
                    self._keystone.KS_MODE_MIPS32 + self._keystone.KS_MODE_LITTLE_ENDIAN,
                )
                encoded, _ = engine.asm(normalized, address)
                data = bytes(encoded[:4])
                if len(data) == 4:
                    return data
            except Exception:
                pass
        try:
            return assemble_fallback(normalized, address)
        except Exception:
            return None

    def disassemble(self, data: bytes, address: int) -> str:
        if len(data) != 4:
            return "word 0x00000000"
        if self._capstone is not None:
            engine = self._capstone.Cs(
                self._capstone.CS_ARCH_MIPS,
                self._capstone.CS_MODE_MIPS32 + self._capstone.CS_MODE_LITTLE_ENDIAN,
            )
            engine.detail = False
            result = next(engine.disasm(data, address), None)
            if result is not None:
                operands = f" {result.op_str}" if result.op_str else ""
                return f"{result.mnemonic}{operands}"
        return disassemble_fallback(int.from_bytes(data, "little"), address)

    def bytes_text(self, data: bytes) -> str:
        return " ".join(f"{value:02X}" for value in data)


def _module_exists(name: str) -> bool:
    try:
        import_module(name)
    except ModuleNotFoundError:
        return False
    return True


def _strip_comment(text: str) -> str:
    return text.split(";", 1)[0]
