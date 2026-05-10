from src.core.binary_workbench.mips_r3000a import PsxMipsR3000ACodec
from src.modules.contracts import CPUArchCodec


PSX_MIPS_R3000A_DISPLAY_NAME = "PSX - Mips R3000A"


def binary_workbench_codec_for(display_name: str) -> CPUArchCodec:
    if display_name == PSX_MIPS_R3000A_DISPLAY_NAME:
        return PsxMipsR3000ACodec()
    return PsxMipsR3000ACodec()
