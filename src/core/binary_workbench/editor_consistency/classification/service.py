from __future__ import annotations

from dataclasses import dataclass

from src.core.binary_workbench.editor_consistency.models import (
    ChangeKind,
    ContributionSnapshot,
    DirtyRange,
)
from src.core.binary_workbench.mips_r3000a.comments import strip_comment
from src.core.binary_workbench.mips_r3000a.preprocessor import (
    is_core_mips_instruction,
)
from src.core.binary_workbench.mips_r3000a.pseudo_instructions import (
    expand_pseudo_instruction,
)
from src.core.binary_workbench.mips_r3000a.source_line_rows import (
    instruction_code,
    split_label,
)
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES


@dataclass(frozen=True)
class LineChange:
    """Describe the byte and symbol impact of one source line change."""

    kind: ChangeKind
    previous_size: int
    current_size: int


def classify_line_change(
    previous_size: int,
    current_size: int,
    *,
    line_count_changed: bool = False,
    label_changed: bool = False,
) -> LineChange:
    """Classify a line using emitted size rather than keyboard activity."""

    structural = line_count_changed or previous_size != current_size
    if structural:
        kind = ChangeKind.STRUCTURAL
    elif label_changed:
        kind = ChangeKind.LOCAL_DEPENDENCY
    else:
        kind = ChangeKind.LOCAL
    return LineChange(kind, max(0, previous_size), max(0, current_size))


def merge_dirty_ranges(
    ranges: tuple[DirtyRange, ...] | list[DirtyRange],
    added: DirtyRange,
) -> tuple[DirtyRange, ...]:
    """Merge touching dirty ranges into a compact sorted tuple."""

    pending = sorted((*ranges, added), key=lambda item: (item.first, item.last))
    merged: list[DirtyRange] = []
    for item in pending:
        normalized = DirtyRange(max(0, item.first), max(item.first, item.last))
        if not merged or normalized.first > merged[-1].last + 1:
            merged.append(normalized)
            continue
        previous = merged[-1]
        merged[-1] = DirtyRange(previous.first, max(previous.last, normalized.last))
    return tuple(merged)


def declared_label(text: str) -> str:
    """Return the normalized label declared by one source line."""

    label, _ = split_label(strip_comment(text).strip())
    return label


def index_label_offsets(
    lines: tuple[str, ...],
    contributions: ContributionSnapshot,
) -> dict[str, str]:
    """Index label offsets without assembling or resolving source operands.

    Lazy Assembly tabs intentionally keep unopened rows unassembled.  A zero
    contribution for one of those rows therefore means "not materialized",
    not necessarily "does not emit bytes".  Recognized instruction mnemonics
    provide the cheap fallback needed by the explicit Labels request.
    """

    labels: dict[str, str] = {}
    offset = 0
    line_index = 0
    for chunk in contributions.chunks:
        for size in chunk:
            if line_index >= len(lines):
                return labels
            name = declared_label(lines[line_index])
            if name:
                labels[name] = f"0x{offset:08X}"
            offset += size or _source_line_size_hint(lines[line_index])
            line_index += 1
    for line in lines[line_index:]:
        name = declared_label(line)
        if name:
            labels[name] = f"0x{offset:08X}"
    return labels


def index_label_lines(lines: tuple[str, ...]) -> dict[str, int]:
    """Map normalized label names to authoritative source block numbers."""

    return {
        name.lower(): index
        for index, line in enumerate(lines)
        if (name := declared_label(line))
    }


def _source_line_size_hint(line: str) -> int:
    """Infer one lazy row's word contribution without validating operands."""

    expanded = expand_pseudo_instruction(line)
    return (
        BINARY_WORKBENCH_ROW_BYTES
        if expanded
        and is_core_mips_instruction(instruction_code(expanded[0]))
        else 0
    )
