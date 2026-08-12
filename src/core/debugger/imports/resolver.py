from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from src.core.binary_workbench.codec_registry import binary_workbench_codec_for
from src.core.binary_workbench.mips_r3000a.symbol_resolver import MipsSymbolResolver
from src.core.debugger.directives.constants import CURRENT_FILE
from src.core.debugger.imports.source import (
    DebuggerAssemblySource,
    DebuggerResolvedImport,
)
from src.core.debugger.imports.parsing.document import debugger_source_document
from src.core.debugger.models.session import (
    DebuggerDirectiveDocument,
    DebuggerError,
    DebuggerErrorCode,
)

SourceLoader = Callable[[Path], DebuggerAssemblySource]


def resolve_debugger_imports(
    main_source: DebuggerAssemblySource,
    document: DebuggerDirectiveDocument,
    source_loader: SourceLoader,
) -> tuple[DebuggerResolvedImport, ...]:
    """Resolve and assemble all imports or fail without returning partial data."""

    root = main_source.path.resolve()
    output: list[DebuggerResolvedImport] = []
    for directive in document.imports:
        if directive.source.casefold() == CURRENT_FILE:
            output.append(
                _assemble(
                    main_source,
                    document,
                    directive.address,
                    CURRENT_FILE,
                )
            )
            continue
        target = _import_path(root.parent, directive.source, directive.line)
        output.extend(
            _resolve_file(
                target,
                directive.address,
                root,
                main_source,
                source_loader,
                (root,),
                directive.data_only,
            )
        )
    return tuple(output)


def _resolve_file(
    path: Path,
    address: int,
    root: Path,
    main_source: DebuggerAssemblySource,
    source_loader: SourceLoader,
    chain: tuple[Path, ...],
    data_only: bool = False,
) -> list[DebuggerResolvedImport]:
    """Resolve one source recursively while detecting only active-chain cycles."""

    resolved = path.resolve()
    if resolved in chain:
        cycle = " -> ".join(item.name for item in (*chain, resolved))
        raise DebuggerError(
            DebuggerErrorCode.IMPORT_CYCLE,
            f"Circular debugger import detected: {cycle}",
            details={"chain": [str(item) for item in (*chain, resolved)]},
        )
    try:
        source = source_loader(resolved)
    except DebuggerError:
        raise
    except Exception as error:
        raise DebuggerError(
            DebuggerErrorCode.IMPORT_FAILED,
            f"Unable to load debugger import {resolved}: {error}",
        ) from error
    document = debugger_source_document(source, main_file=False)
    imports: list[DebuggerResolvedImport] = []
    next_chain = (*chain, resolved)
    for directive in document.imports:
        if directive.source.casefold() == CURRENT_FILE:
            imports.append(
                _assemble(
                    main_source,
                    debugger_source_document(main_source),
                    directive.address,
                    CURRENT_FILE,
                )
            )
            continue
        child = _import_path(root.parent, directive.source, directive.line)
        imports.extend(
            _resolve_file(
                child,
                directive.address,
                root,
                main_source,
                source_loader,
                next_chain,
                directive.data_only,
            )
        )
    imports.append(
        _assemble(
            source,
            document,
            address,
            _relative_origin(root.parent, source.path),
            data_only,
        )
    )
    return imports


def _assemble(
    source: DebuggerAssemblySource,
    document: DebuggerDirectiveDocument,
    address: int,
    origin: str,
    data_only: bool = False,
) -> DebuggerResolvedImport:
    """Assemble one parsed source through its existing architecture codec."""

    codec = binary_workbench_codec_for(source.architecture)
    rows = codec.build_source_line_rows(
        list(document.assembly_lines),
        ["File"],
        {"File": "0x00000000"},
        address,
        labels=source.labels,
        variables=source.variables,
        equates=source.equates,
        reject_invalid=True,
        symbol_resolver=MipsSymbolResolver(
            source.labels,
            source.variables,
            source.equates,
            jump_file_offset_base=0,
        ),
    )
    if rows is None:
        raise DebuggerError(
            DebuggerErrorCode.ASSEMBLY_FAILED,
            f"Unable to assemble debugger import {source.path}.",
            details={"path": str(source.path), "workspace": source.workspace},
        )
    data = b"".join(bytes.fromhex(row.bytes_text.replace(" ", "")) for row in rows)
    return DebuggerResolvedImport(
        source.path,
        source.workspace,
        source.architecture,
        address,
        data,
        origin,
        tuple(rows),
        data_only,
    )


def _relative_origin(root: Path, source: Path) -> str:
    """Format an imported source relative to current_file, without its suffix."""

    relative = source.resolve().relative_to(root.resolve())
    return relative.with_suffix("").as_posix()


def _import_path(root: Path, value: str, line: int) -> Path:
    """Resolve an `.asm` import inside the main source directory tree."""

    target = (root / value).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as error:
        raise DebuggerError(
            DebuggerErrorCode.IMPORT_FAILED,
            f"Import on line {line} must stay inside the main source directory.",
            line=line,
        ) from error
    if target.suffix.casefold() not in {".asm", ".s"}:
        raise DebuggerError(
            DebuggerErrorCode.IMPORT_FAILED,
            f"Import on line {line} must reference an assembly file.",
            line=line,
        )
    return target
