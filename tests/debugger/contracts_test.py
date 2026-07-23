import pytest

from src.core.debugger import (
    BWDebugger,
    BWDebuggerPSXR3000A,
    BWDebuggerRegs,
    DebuggerEndianness,
    DebuggerError,
    DebuggerErrorCode,
    DebuggerSessionState,
)
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
)


def test_psx_debugger_exposes_architecture_metadata_dynamically():
    debugger = BWDebuggerPSXR3000A()

    assert isinstance(debugger, BWDebugger)
    assert isinstance(debugger.registers, BWDebuggerRegs)
    assert debugger.architecture == BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME
    assert debugger.endianness == DebuggerEndianness.LITTLE
    assert debugger.state == DebuggerSessionState.READY
    assert debugger.registers.pc_register == "pc"
    assert debugger.registers.stack_register == "sp"
    assert debugger.step_rules.delay_slots == 1
    assert debugger.step_rules.call_mnemonics == ("jal", "jalr")


def test_psx_registers_support_names_aliases_sizes_and_zero_semantics():
    registers = BWDebuggerPSXR3000A().registers

    registers.write("$r29", 0x801DFF00)
    registers.write("$zero", 99)

    assert registers.read("sp") == 0x801DFF00
    assert registers.read("29") == 0x801DFF00
    assert registers.read("zero") == 0
    assert registers.register_size("pc") == 32
    assert len(registers.descriptors) == 35


def test_psx_debugger_reports_missing_backend_as_controlled_error():
    debugger = BWDebuggerPSXR3000A()

    with pytest.raises(DebuggerError) as captured:
        debugger.step()

    assert captured.value.code == DebuggerErrorCode.BACKEND_UNAVAILABLE
    assert debugger.last_error is captured.value
    assert debugger.state == DebuggerSessionState.ERROR


def test_restart_resets_registers_and_preserves_breakpoint_contract():
    debugger = BWDebuggerPSXR3000A()
    debugger.pc = 0x801D9274
    debugger.stop()

    debugger.restart()

    assert debugger.pc == 0
    assert debugger.state == DebuggerSessionState.READY
    assert debugger.breakpoints == ()

