import pytest

from src.core.debugger import (
    DebuggerError,
    DebuggerErrorCode,
    parse_debugger_directives,
)
from src.core.debugger.directives.constants import PSX_SCRATCH_HEADER
from src.modules.binary_workbench_dtos import BinaryWorkbenchStateDTO
from src.presentation.ui.components.binary_workbench.tabs.tab_context_factory import (
    create_scratch_tab,
)


VALID_SOURCE = [
    "* virtual_memory_range 0x80000000 0x801DFFFF",
    "* import scratch_code.asm 0x801D9200",
    "* import current_file ENTRY",
    "* define $pc ENTRY",
    "* define $sp 0x801DFF00",
    "* define $gp 0x8009AF08",
    "* ignore $pc 0x80024D34",
    "start: nop",
]


def test_parser_returns_structured_directives_and_preserves_line_numbers():
    document = parse_debugger_directives(VALID_SOURCE, {"ENTRY": "0x801D9274"})

    assert document.memory_range is not None
    assert document.memory_range.start == 0x80000000
    assert document.memory_range.end == 0x801DFFFF
    assert [(item.source, item.address) for item in document.imports] == [
        ("scratch_code.asm", 0x801D9200),
        ("current_file", 0x801D9274),
    ]
    assert document.register_values[0].register == "$pc"
    assert document.register_values[0].value == 0x801D9274
    assert document.ignored_addresses[0].address == 0x80024D34
    assert document.assembly_lines[:7] == ("",) * 7
    assert document.assembly_lines[7] == "start: nop"


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (["nop"], "first line"),
        (["* virtual_memory_range 0x2 0x1"], "lower"),
        (["* virtual_memory_range 0x1 0x2", "* define $pc"], "exactly 2"),
        (["* virtual_memory_range 0x1 0x2", "* define pc 0x1"], "register"),
        (["* virtual_memory_range 0x1 0x2", "* define $pc 123"], "hexadecimal"),
        (["* virtual_memory_range 0x1 0x2", "* unknown 0x1 0x2"], "Unknown"),
    ],
)
def test_parser_rejects_invalid_directive_syntax(source, message):
    with pytest.raises(DebuggerError) as captured:
        parse_debugger_directives(source)

    assert captured.value.code == DebuggerErrorCode.INVALID_DIRECTIVE
    assert message in captured.value.message


def test_parser_accepts_only_symbols_whose_complete_value_is_hexadecimal():
    source = [
        "* virtual_memory_range START END",
        "* define $pc BAD",
    ]

    with pytest.raises(DebuggerError) as captured:
        parse_debugger_directives(
            source,
            {"START": "0x80000000", "END": "0x801DFFFF", "BAD": "0x10 + 4"},
        )

    assert captured.value.line == 2
    assert "hexadecimal Symbol" in captured.value.message


def test_parser_rejects_duplicate_range_and_directive_after_instruction():
    duplicate = [
        "* virtual_memory_range 0x1 0x10",
        "* virtual_memory_range 0x2 0x20",
    ]
    after_instruction = [
        "* virtual_memory_range 0x1 0x10",
        "nop",
        "* define $pc 0x4",
    ]

    with pytest.raises(DebuggerError, match="Only one"):
        parse_debugger_directives(duplicate)
    with pytest.raises(DebuggerError, match="before assembly"):
        parse_debugger_directives(after_instruction)


def test_imported_source_does_not_require_or_accept_virtual_memory_range():
    document = parse_debugger_directives(
        ["* import child.asm 0x80001000", "nop"],
        main_file=False,
    )

    assert document.memory_range is None
    assert document.imports[0].source == "child.asm"


def test_label_only_line_does_not_count_as_first_valid_instruction():
    document = parse_debugger_directives(
        [
            "* virtual_memory_range 0x1000 0x1FFF",
            "start:",
            "* define $pc 0x1000",
            "nop",
        ]
    )

    assert document.register_values[0].value == 0x1000


def test_psx_scratch_starts_with_the_complete_debugger_header():
    """Seed new PSX scratch sources with every required debugger directive."""

    scratch = create_scratch_tab(BinaryWorkbenchStateDTO())

    assert tuple(row.instruction for row in scratch.rows[:4]) == PSX_SCRATCH_HEADER
    assert all(not row.bytes_text for row in scratch.rows[:4])
