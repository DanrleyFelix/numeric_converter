"""Unicorn register identifiers for the PSX R3000A backend."""

from unicorn import mips_const

from src.core.debugger.psx_r3000a.registers import GPR_NAMES

SPECIAL_REGISTER_IDS = {
    "hi": mips_const.UC_MIPS_REG_HI,
    "lo": mips_const.UC_MIPS_REG_LO,
    "pc": mips_const.UC_MIPS_REG_PC,
}
REGISTER_IDS = {
    **{
        name: getattr(mips_const, f"UC_MIPS_REG_{index}")
        for index, name in enumerate(GPR_NAMES)
    },
    **SPECIAL_REGISTER_IDS,
}
