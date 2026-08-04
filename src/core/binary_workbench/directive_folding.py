from dataclasses import dataclass

from src.core.binary_workbench.mips_r3000a.comments import strip_comment
from src.core.debugger.directives.constants import DEBUGGER_DIRECTIVE_NAMES
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


@dataclass(frozen=True)
class DirectiveFoldRegion:
    """Describe the leading debugger-directive group shown as one visual fold."""

    header_row: int
    first_hidden_row: int
    last_hidden_row: int

    def contains(self, row: int) -> bool:
        """Return whether a row belongs to the complete directive group."""

        return self.header_row <= row <= self.last_hidden_row


def debugger_directive_fold_region(
    rows: list[BinaryWorkbenchRowDTO],
) -> DirectiveFoldRegion | None:
    """Find consecutive leading debugger directives without changing source rows."""

    first: int | None = None
    last: int | None = None
    for index, row in enumerate(rows):
        code = strip_comment(row.instruction).strip()
        if not code:
            continue
        if not _recognized_directive(code):
            break
        first = index if first is None else first
        last = index
    if first is None or last is None or first == last:
        return None
    return DirectiveFoldRegion(first, first + 1, last)


def _recognized_directive(code: str) -> bool:
    """Recognize one supported debugger directive by its command token."""

    if not code.startswith("*"):
        return False
    parts = code[1:].strip().split(maxsplit=1)
    return bool(parts and parts[0].casefold() in DEBUGGER_DIRECTIVE_NAMES)
