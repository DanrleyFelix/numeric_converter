from src.core.binary_workbench.mips_r3000a import PsxMipsR3000ACodec
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME
from src.modules.contracts import CPUArchCodec


def binary_workbench_codec_for(display_name: str) -> CPUArchCodec:
    if display_name == BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME:
        return PsxMipsR3000ACodec()
    return PsxMipsR3000ACodec()


def binary_workbench_worker_codec_for(display_name: str) -> CPUArchCodec:
    """Return an assembler instance that avoids native engines in worker threads."""

    if display_name == BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME:
        return PsxMipsR3000ACodec(use_native_engines=False)
    return PsxMipsR3000ACodec(use_native_engines=False)
