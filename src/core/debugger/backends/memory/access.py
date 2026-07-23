"""Recover PSX virtual load/store addresses from Unicorn memory hooks."""

from collections.abc import Mapping

from unicorn import UcError

from src.core.debugger.backends.errors.access import psx_memory_access_details
from src.core.debugger.backends.memory.mapping import unicorn_memory_address


def psx_hook_memory_address(
    engine,
    physical_address: int,
    pc_register_id: int,
    register_ids: Mapping[str, int],
) -> int:
    """Resolve the virtual effective address behind one physical Unicorn hook."""

    try:
        pc = int(engine.reg_read(pc_register_id)) & 0xFFFFFFFF
        instruction = bytes(engine.mem_read(unicorn_memory_address(pc), 4))
        registers = {
            name: int(engine.reg_read(register_id)) & 0xFFFFFFFF
            for name, register_id in register_ids.items()
        }
    except (KeyError, UcError):
        return physical_address
    address, size = psx_memory_access_details(instruction, registers, physical_address)
    return address if size else physical_address
