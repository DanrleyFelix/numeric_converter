from pathlib import Path

import pytest

from src.core.debugger import DebuggerError, DebuggerErrorCode, parse_debugger_directives
from src.core.debugger.imports.completion.provider import ImportCompletionProvider
from src.core.debugger.imports.resolver import resolve_debugger_imports
from src.core.debugger.imports.source import DebuggerAssemblySource
from src.core.debugger.memory.builder import build_debugger_memory
from src.core.debugger.psx_r3000a.registers import PsxR3000ARegisters
from src.core.debugger.session.factory import _debugger_instructions
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
)


def _source(path: Path, lines: list[str], workspace: str | None = None):
    """Create one workspace-aware source for resolver tests."""

    return DebuggerAssemblySource(
        path,
        workspace,
        tuple(lines),
        BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
        {},
        {},
        {},
    )


def test_resolver_assembles_current_file_and_recursive_imports(tmp_path: Path):
    main_path = tmp_path / "main.asm"
    child_path = tmp_path / "child.asm"
    nested_path = tmp_path / "sub" / "nested.asm"
    main = _source(
        main_path,
        [
            "* virtual_memory_range 0x80000000 0x8000FFFF",
            "* import current_file 0x80000100",
            "* import child.asm 0x80000200",
            "* define $pc 0x80000100",
            "nop",
        ],
        "main-workspace.json",
    )
    child = _source(
        child_path,
        ["* import sub/nested.asm 0x80000300", "addiu $v0, $zero, 1"],
        "child-workspace.json",
    )
    nested = _source(nested_path, ["nop"], "nested-workspace.json")
    sources = {child_path.resolve(): child, nested_path.resolve(): nested}
    document = parse_debugger_directives(main.lines, main.symbols)

    imports = resolve_debugger_imports(main, document, sources.__getitem__)

    assert [(item.path.name, item.address, item.size) for item in imports] == [
        ("main.asm", 0x80000100, 4),
        ("nested.asm", 0x80000300, 4),
        ("child.asm", 0x80000200, 4),
    ]
    assert imports[-1].workspace == "child-workspace.json"
    assert [item.origin for item in imports] == [
        "current_file",
        "sub/nested",
        "child",
    ]


def test_resolver_allows_same_file_at_different_addresses(tmp_path: Path):
    main = _source(
        tmp_path / "main.asm",
        [
            "* virtual_memory_range 0x80000000 0x8000FFFF",
            "* import child.asm 0x80000100",
            "* import child.asm 0x80000200",
            "* define $pc 0x80000100",
        ],
    )
    child = _source(tmp_path / "child.asm", ["nop"])
    document = parse_debugger_directives(main.lines)

    imports = resolve_debugger_imports(main, document, lambda _path: child)

    assert [item.address for item in imports] == [0x80000100, 0x80000200]


def test_resolver_does_not_apply_current_file_base_twice_to_jump_labels(
    tmp_path: Path,
):
    """Keep debugger JAL bytes equal to the editor's file-offset projection."""

    path = tmp_path / "main.asm"
    source = DebuggerAssemblySource(
        path,
        None,
        (
            "* virtual_memory_range 0x80000000 0x801DFFFF",
            "* import current_file 0x8000F800",
            "* define $pc 0x8000F804",
            "* define $sp 0x801FFF00",
            "slot_to_ptr: nop",
            "jal slot_to_ptr",
        ),
        BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
        {"slot_to_ptr": "0x00000000"},
        {},
        {},
    )

    imported = resolve_debugger_imports(
        source,
        parse_debugger_directives(source.lines, source.symbols),
        lambda _path: source,
    )[0]

    assert imported.rows[-1].offsets["File"] == "0x8000F804"
    assert imported.rows[-1].bytes_text == "00 3E 00 0C"


def test_import_completion_lists_only_safe_supported_children(tmp_path: Path):
    """Keep import completion hierarchical, bounded and source-relative."""

    source = tmp_path / "main.asm"
    source.write_text("nop", encoding="utf-8")
    (tmp_path / "child.asm").write_text("nop", encoding="utf-8")
    (tmp_path / "child.s").write_text("nop", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("nop", encoding="utf-8")
    (tmp_path / "has space.asm").write_text("nop", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "leaf.asm").write_text("nop", encoding="utf-8")
    provider = ImportCompletionProvider()

    assert [item.value for item in provider.complete(source, "")] == [
        "nested/",
        "child.asm",
        "child.s",
        "current_file",
    ]
    assert [item.value for item in provider.complete(source, "nested/")] == [
        "nested/leaf.asm"
    ]
    assert provider.complete(source, "../") == ()


def test_unsaved_import_completion_offers_only_current_file():
    """Avoid filesystem access when a Scratch Code has no source path."""

    provider = ImportCompletionProvider()

    assert [item.value for item in provider.complete(None, "cur")] == ["current_file"]
    assert provider.complete(None, "nested/") == ()


def test_resolver_reports_the_complete_circular_dependency_chain(tmp_path: Path):
    main_path = tmp_path / "main.asm"
    first_path = tmp_path / "first.asm"
    second_path = tmp_path / "second.asm"
    main = _source(
        main_path,
        [
            "* virtual_memory_range 0x80000000 0x8000FFFF",
            "* import first.asm 0x80000100",
            "* define $pc 0x80000100",
        ],
    )
    sources = {
        first_path.resolve(): _source(first_path, ["* import second.asm 0x80000200"]),
        second_path.resolve(): _source(second_path, ["* import first.asm 0x80000300"]),
    }

    with pytest.raises(DebuggerError) as captured:
        resolve_debugger_imports(
            main,
            parse_debugger_directives(main.lines),
            sources.__getitem__,
        )

    assert captured.value.code == DebuggerErrorCode.IMPORT_CYCLE
    assert "main.asm -> first.asm -> second.asm -> first.asm" in captured.value.message
    assert len(captured.value.details["chain"]) == 4


def test_resolver_rejects_import_outside_main_directory(tmp_path: Path):
    root = tmp_path / "root"
    main = _source(
        root / "main.asm",
        [
            "* virtual_memory_range 0x80000000 0x8000FFFF",
            "* import ../outside.asm 0x80000100",
            "* define $pc 0x80000100",
        ],
    )

    with pytest.raises(DebuggerError) as captured:
        resolve_debugger_imports(
            main,
            parse_debugger_directives(main.lines),
            lambda path: _source(path, ["nop"]),
        )

    assert captured.value.code == DebuggerErrorCode.IMPORT_FAILED
    assert "inside the main source directory" in captured.value.message


def test_data_file_is_mapped_but_omitted_from_debugger_instructions(tmp_path: Path):
    """Keep data readable without presenting its words as executable code."""

    main_path = tmp_path / "main.asm"
    code_path = tmp_path / "helpers.asm"
    data_path = tmp_path / "data" / "deck_entry_bytes.asm"
    main = _source(
        main_path,
        [
            "* virtual_memory_range 0x80000000 0x801DFFFF",
            "* import current_file 0x8000F800",
            "* import helpers.asm 0x80010000",
            "* import data_file data/deck_entry_bytes.asm 0x801A7E20",
            "* define $pc 0x8000F800",
            "* define $sp 0x801DFFF0",
            "nop",
        ],
    )
    code = _source(code_path, ["nop"])
    data = _source(data_path, ["word 0x00120300"])

    document = parse_debugger_directives(main.lines, main.symbols)
    imports = resolve_debugger_imports(
        main,
        document,
        lambda path: {
            code_path.resolve(): code,
            data_path.resolve(): data,
        }[path],
    )
    memory = build_debugger_memory(document, imports, PsxR3000ARegisters())
    instructions = _debugger_instructions(imports, memory)

    assert imports[1].origin == "helpers"
    assert imports[1].data_only is False
    assert imports[2].origin == "data/deck_entry_bytes"
    assert imports[2].data_only is True
    assert memory.data[0x1A7E20:0x1A7E24] == bytes.fromhex("00 03 12 00")
    assert [item.address for item in instructions] == [0x8000F800, 0x80010000]

