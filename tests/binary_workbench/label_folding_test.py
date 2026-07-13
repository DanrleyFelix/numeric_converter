from src.core.binary_workbench.label_folding import label_fold_regions
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


def _row(instruction: str) -> BinaryWorkbenchRowDTO:
    return BinaryWorkbenchRowDTO(instruction=instruction)


def test_label_fold_regions_stop_after_return_or_before_next_label():
    rows = [
        _row("start: addiu $v0, $zero, 1"),
        _row("nop"),
        _row("jr $ra"),
        _row("unowned: nop"),
        _row("addiu $v0, $zero, 2"),
        _row("next: nop"),
        _row("addu $v0, $v1, $v2"),
        _row("jr ra ; register marker is optional"),
        _row("nop"),
    ]

    regions = label_fold_regions(rows)

    assert [(item.label, item.label_row, item.first_hidden_row, item.last_hidden_row) for item in regions] == [
        ("start", 0, 1, 2),
        ("unowned", 3, 4, 4),
        ("next", 5, 6, 7),
    ]
