from src.core.binary_workbench.directive_folding import debugger_directive_fold_region
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


def _rows(lines: list[str]) -> list[BinaryWorkbenchRowDTO]:
    """Build source-only rows for directive fold detection."""

    return [BinaryWorkbenchRowDTO(instruction=line) for line in lines]


def test_directive_fold_region_contains_every_leading_supported_directive():
    """Group all supported top directives and stop before assembly code."""

    region = debugger_directive_fold_region(
        _rows(
            [
                "* virtual_memory_range 0x80000000 0x801FFFFF",
                "* import current_file 0x80000000",
                "* define $sp 0x801FFFF0",
                "* ignore $v0 0x80000020",
                "start: nop",
                "* define $pc 0x80000000",
            ]
        )
    )

    assert region is not None
    assert (region.header_row, region.first_hidden_row, region.last_hidden_row) == (0, 1, 3)


def test_single_or_unknown_directive_does_not_create_a_visual_group():
    """Avoid displaying a fold control when there is no group to collapse."""

    assert debugger_directive_fold_region(_rows(["* define $sp 0x801FFFF0", "nop"])) is None
    assert debugger_directive_fold_region(_rows(["* unknown value", "* define $sp 0x801FFFF0"])) is None
