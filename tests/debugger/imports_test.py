from pathlib import Path

import pytest

from src.core.debugger import DebuggerError, DebuggerErrorCode, parse_debugger_directives
from src.core.debugger.imports.resolver import resolve_debugger_imports
from src.core.debugger.imports.source import DebuggerAssemblySource
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

