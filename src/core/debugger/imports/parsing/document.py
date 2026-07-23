from __future__ import annotations

from src.core.binary_workbench.codec_registry import binary_workbench_codec_for
from src.core.debugger.directives.parser import parse_debugger_directives
from src.core.debugger.imports.source import DebuggerAssemblySource
from src.core.debugger.models.session import DebuggerDirectiveDocument


def debugger_source_document(
    source: DebuggerAssemblySource,
    main_file: bool = True,
) -> DebuggerDirectiveDocument:
    """Parse directives using the source architecture's instruction grammar."""

    codec = binary_workbench_codec_for(source.architecture)
    return parse_debugger_directives(
        source.lines,
        source.symbols,
        main_file=main_file,
        is_instruction=lambda text: bool(codec.instruction_code(text).strip()),
    )
