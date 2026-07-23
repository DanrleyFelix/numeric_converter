from __future__ import annotations

from dataclasses import dataclass

from src.core.binary_workbench.codec_registry import binary_workbench_codec_for
from src.core.debugger.directives.constants import CURRENT_FILE
from src.core.debugger.imports.resolver import SourceLoader, resolve_debugger_imports
from src.core.debugger.imports.parsing.document import debugger_source_document
from src.core.debugger.imports.source import (
    DebuggerAssemblySource,
    DebuggerResolvedImport,
)
from src.core.debugger.memory.builder import build_debugger_memory
from src.core.debugger.memory.image import DebuggerMemoryImage
from src.core.debugger.models.session import (
    DebuggerDirectiveDocument,
    DebuggerError,
    DebuggerErrorCode,
    DebuggerInstruction,
)
from src.core.debugger.psx_r3000a.debugger import BWDebuggerPSXR3000A


@dataclass(frozen=True)
class DebuggerSessionBundle:
    """Hold every validated artifact used by one debugger window."""

    debugger: BWDebuggerPSXR3000A
    document: DebuggerDirectiveDocument
    imports: tuple[DebuggerResolvedImport, ...]
    memory: DebuggerMemoryImage


def create_debugger_session(
    main_source: DebuggerAssemblySource,
    source_loader: SourceLoader,
) -> DebuggerSessionBundle:
    """Create a complete PSX session without exposing partial construction."""

    debugger = BWDebuggerPSXR3000A()
    if main_source.architecture != debugger.architecture:
        raise DebuggerError(
            DebuggerErrorCode.BACKEND_UNAVAILABLE,
            f"Debugger backend does not support architecture {main_source.architecture}.",
        )
    document = debugger_source_document(main_source)
    _validate_required_configuration(document, debugger)
    imports = resolve_debugger_imports(main_source, document, source_loader)
    if any(item.architecture != debugger.architecture for item in imports):
        raise DebuggerError(
            DebuggerErrorCode.IMPORT_FAILED,
            "All debugger imports must use the main source architecture.",
        )
    _validate_current_file_range(document, imports)
    memory = build_debugger_memory(document, imports, debugger.registers)
    instructions = _debugger_instructions(imports, memory)
    debugger.configure_memory(memory, instructions)
    return DebuggerSessionBundle(debugger, document, imports, memory)


def _debugger_instructions(
    imports: tuple[DebuggerResolvedImport, ...],
    memory: DebuggerMemoryImage,
) -> tuple[DebuggerInstruction, ...]:
    """Convert loaded rows into instruction records with last-import priority."""

    output: dict[int, DebuggerInstruction] = {}
    for imported in imports:
        codec = binary_workbench_codec_for(imported.architecture)
        for row in imported.rows:
            if not row.bytes_text:
                continue
            address = int(row.offsets.get("File", "0x0"), 0)
            data = bytes.fromhex(row.bytes_text.replace(" ", ""))
            if not memory.contains(address, len(data)):
                continue
            output[address] = DebuggerInstruction(
                address,
                data,
                codec.disassemble(data, address),
                imported.origin,
            )
    return tuple(output[address] for address in sorted(output))


def _validate_required_configuration(
    document: DebuggerDirectiveDocument,
    debugger: BWDebuggerPSXR3000A,
) -> None:
    """Reject a session missing one required PSX bootstrap directive."""

    if document.memory_range is None:
        raise _required_error("virtual_memory_range")
    if not any(item.source.casefold() == CURRENT_FILE for item in document.imports):
        raise _required_error("import current_file")
    defined = {
        descriptor.name
        for item in document.register_values
        for descriptor in debugger.registers.descriptors
        if item.register.lstrip("$").casefold()
        in {descriptor.name.casefold(), *(alias.casefold() for alias in descriptor.aliases)}
    }
    for register in (debugger.registers.stack_register, debugger.registers.pc_register):
        if register not in defined:
            raise _required_error(f"initial ${register} value")


def _required_error(configuration: str) -> DebuggerError:
    """Create an actionable error for one missing debugger configuration."""

    return DebuggerError(
        DebuggerErrorCode.INVALID_DIRECTIVE,
        f"Debugger requires {configuration}.",
    )


def _validate_current_file_range(
    document: DebuggerDirectiveDocument,
    imports: tuple[DebuggerResolvedImport, ...],
) -> None:
    """Require effective current-file bytes inside the declared virtual range."""

    memory = document.memory_range
    loaded = memory is not None and any(
        item.origin.casefold() == CURRENT_FILE
        and max(memory.start, item.address) <= min(memory.end, item.end)
        for item in imports
    )
    if not loaded:
        raise _required_error("a valid import current_file inside virtual_memory_range")
