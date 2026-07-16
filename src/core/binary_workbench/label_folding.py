from dataclasses import dataclass

from src.core.binary_workbench.mips_r3000a.comments import strip_comment
from src.core.binary_workbench.mips_r3000a.source_line_rows import split_label
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


@dataclass(frozen=True)
class LabelFoldRegion:
    """Describes the viewport rows controlled by one assembly label."""

    label: str
    label_row: int
    first_hidden_row: int
    last_hidden_row: int

    def contains(self, row: int) -> bool:
        """Return whether a row belongs to the collapsible label body."""

        return self.first_hidden_row <= row <= self.last_hidden_row


def label_fold_regions(rows: list[BinaryWorkbenchRowDTO]) -> list[LabelFoldRegion]:
    """Build fold regions ending at the next label or after ``jr $ra``."""

    regions: list[LabelFoldRegion] = []
    for label_row, row in enumerate(rows):
        label, code = _label_and_code(row.instruction)
        if not label:
            continue
        first_hidden = label_row + 1
        last_hidden = (
            _delay_slot_end(rows, label_row)
            if _is_return_instruction(code)
            else _region_end(rows, first_hidden)
        )
        if first_hidden <= last_hidden:
            regions.append(
                LabelFoldRegion(label, label_row, first_hidden, last_hidden)
            )
    return regions


def _region_end(rows: list[BinaryWorkbenchRowDTO], start: int) -> int:
    """Find the inclusive end row for a label body."""

    for index in range(start, len(rows)):
        label, code = _label_and_code(rows[index].instruction)
        if label:
            return index - 1
        if _is_return_instruction(code):
            return _delay_slot_end(rows, index)
    return len(rows) - 1


def _delay_slot_end(rows: list[BinaryWorkbenchRowDTO], return_row: int) -> int:
    """Include the next executable source line without ever hiding a label."""

    for index in range(return_row + 1, len(rows)):
        label, code = _label_and_code(rows[index].instruction)
        if label:
            return return_row
        if code:
            return index
    return len(rows) - 1


def _label_and_code(instruction: str) -> tuple[str, str]:
    """Split a source line into its valid label and executable code."""

    return split_label(strip_comment(instruction).strip())


def _is_return_instruction(code: str) -> bool:
    """Recognize the return instruction accepted by the assembly editor."""

    tokens = code.replace(",", " ").lower().split()
    return tokens in (["jr", "$ra"], ["jr", "ra"])
