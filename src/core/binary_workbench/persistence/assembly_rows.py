"""Normalize invalid Assembly attempts while byte shifting is locked."""

from __future__ import annotations

from src.core.binary_workbench.mips_r3000a import editor_mips_instruction
from src.core.binary_workbench.mips_r3000a.comments import split_comment
from src.core.binary_workbench.mips_r3000a.preprocessor import raw_mips_instruction
from src.core.binary_workbench.mips_r3000a.source_line_rows import split_label
from src.core.binary_workbench.mips_r3000a.symbol_resolver import MipsSymbolResolver
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_FILE_OFFSET_COLUMN as FILE_OFFSET,
    BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.modules.contracts import CPUArchCodec

INCORRECT_INSTRUCTION = "Incorrect Instruction:"
EMPTY_ATTEMPT = "<empty>"
MAX_ISOLATED_INVALID_INSTRUCTIONS = 4


def normalize_locked_assembly_rows(
    rows: list[BinaryWorkbenchRowDTO],
    codec: CPUArchCodec,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
    fallback_rows: tuple[list[BinaryWorkbenchRowDTO], ...] = (),
) -> list[BinaryWorkbenchRowDTO]:
    """Restore prior valid code and retain an invalid edit as context."""

    fallbacks = _fallback_by_offset(fallback_rows)
    line_fallbacks = _fallback_by_line(len(rows), fallback_rows)
    resolver = MipsSymbolResolver(labels, variables, equates)
    if _has_bulk_invalid_attempts(
        rows,
        codec,
        labels,
        variables,
        equates,
        resolver,
    ):
        # A missing Symbol catalog can make an otherwise valid large source
        # look invalid.  Bulk normalization is destructive, so only isolated
        # invalid edits are eligible for the contextual comment fallback.
        return list(rows)
    return [
        _normalize_row(
            index,
            row,
            codec,
            labels,
            variables,
            equates,
            resolver,
            fallbacks,
            line_fallbacks,
        )
        for index, row in enumerate(rows)
    ]


def _normalize_row(
    index: int,
    row: BinaryWorkbenchRowDTO,
    codec: CPUArchCodec,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
    resolver: MipsSymbolResolver,
    fallbacks: dict[str, BinaryWorkbenchRowDTO],
    line_fallbacks: dict[int, BinaryWorkbenchRowDTO],
) -> BinaryWorkbenchRowDTO:
    fallback = fallbacks.get(row.offsets.get(FILE_OFFSET, "-"))
    if fallback is None:
        fallback = line_fallbacks.get(index)
    if (
        fallback is not None
        and row.instruction == fallback.instruction
        and row.bytes_text == fallback.bytes_text
    ):
        return row
    code, _, comment = split_comment(row.instruction)
    label, instruction = split_label(code.strip())
    attempted = instruction.strip()
    if (
        attempted.startswith("*")
        or _contains_symbol_sigil(attempted)
        or _assembles(
            row.instruction,
            row,
            codec,
            labels,
            variables,
            equates,
            resolver,
        )
    ):
        return row
    previous = _previous_encoding(row, fallback)
    previous_label, restored, previous_comment = _restored_source(
        previous,
        codec,
        preserve_source=previous is not row,
    )
    if restored:
        note = f"{INCORRECT_INSTRUCTION} {attempted or EMPTY_ATTEMPT}"
        retained_comment = comment.strip() or previous_comment
        suffix = f" | {retained_comment}" if retained_comment else ""
        instruction_text = f"{restored}; {note}{suffix}"
        retained_label = label or previous_label
        prefix = f"{retained_label}: " if retained_label else ""
        return BinaryWorkbenchRowDTO(
            offsets=dict(row.offsets),
            instruction=f"{prefix}{instruction_text}",
            bytes_text=previous.bytes_text,
            original_instruction=row.original_instruction,
            original_bytes_text=row.original_bytes_text,
        )
    if not attempted:
        return row
    note = f"{INCORRECT_INSTRUCTION} {attempted}"
    suffix = f" | {comment.strip()}" if comment.strip() else ""
    prefix = f"{label}: " if label else ""
    return BinaryWorkbenchRowDTO(
        offsets=dict(row.offsets),
        instruction=f"{prefix}; {note}{suffix}",
        bytes_text="",
        original_instruction=row.original_instruction,
        original_bytes_text=row.original_bytes_text,
    )


def _has_bulk_invalid_attempts(
    rows: list[BinaryWorkbenchRowDTO],
    codec: CPUArchCodec,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
    resolver: MipsSymbolResolver,
) -> bool:
    """Reject destructive normalization when invalid source is not isolated."""

    invalid_count = 0
    for row in rows:
        code, _, _comment = split_comment(row.instruction)
        _label, instruction = split_label(code.strip())
        attempted = instruction.strip()
        if (
            not attempted
            or attempted.startswith("*")
            or _contains_symbol_sigil(attempted)
            or _assembles(
                row.instruction,
                row,
                codec,
                labels,
                variables,
                equates,
                resolver,
            )
        ):
            continue
        invalid_count += 1
        if invalid_count > MAX_ISOLATED_INVALID_INSTRUCTIONS:
            return True
    return False


def _contains_symbol_sigil(source: str) -> bool:
    """Recognize unresolved legacy/local Symbol syntax before commenting it."""

    return "_" in source or "@" in source


def _assembles(
    source: str,
    row: BinaryWorkbenchRowDTO,
    codec: CPUArchCodec,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
    resolver: MipsSymbolResolver,
) -> bool:
    try:
        offset = int(row.offsets.get(FILE_OFFSET, "0x0"), 16)
    except ValueError:
        offset = 0
    raw = raw_mips_instruction(
        source,
        offset,
        labels,
        variables,
        equates,
        resolver,
    )
    return bool(raw and codec.assemble(raw, offset) is not None)


def _fallback_by_offset(
    groups: tuple[list[BinaryWorkbenchRowDTO], ...],
) -> dict[str, BinaryWorkbenchRowDTO]:
    values: dict[str, BinaryWorkbenchRowDTO] = {}
    for rows in groups:
        for row in rows:
            offset = row.offsets.get(FILE_OFFSET, "-")
            if offset != "-" and row.bytes_text:
                values.setdefault(offset, row)
    return values


def _previous_encoding(
    row: BinaryWorkbenchRowDTO,
    fallback: BinaryWorkbenchRowDTO | None,
) -> BinaryWorkbenchRowDTO:
    if fallback is not None:
        return fallback
    if row.bytes_text:
        return row
    if row.original_bytes_text:
        return BinaryWorkbenchRowDTO(
            row.offsets,
            row.original_instruction,
            row.original_bytes_text,
        )
    return row


def _fallback_by_line(
    row_count: int,
    groups: tuple[list[BinaryWorkbenchRowDTO], ...],
) -> dict[int, BinaryWorkbenchRowDTO]:
    """Match locked 4-to-0 edits by line when document shape did not change."""

    values: dict[int, BinaryWorkbenchRowDTO] = {}
    for rows in groups:
        if len(rows) != row_count:
            continue
        for index, row in enumerate(rows):
            if row.bytes_text:
                values.setdefault(index, row)
    return values


def _restored_source(
    row: BinaryWorkbenchRowDTO,
    codec: CPUArchCodec,
    *,
    preserve_source: bool,
) -> tuple[str, str, str]:
    if preserve_source:
        code, _, comment = split_comment(row.instruction)
        label, instruction = split_label(code.strip())
        if instruction.strip() and not instruction.lstrip().startswith("*"):
            return label, instruction.strip(), comment.strip()
    try:
        offset = int(row.offsets.get(FILE_OFFSET, "0x0"), 16)
        data = bytes.fromhex(row.bytes_text.replace(" ", "")).ljust(
            ROW_BYTES, b"\x00"
        )
    except ValueError:
        return "", "", ""
    return "", editor_mips_instruction(codec.disassemble(data, offset), offset), ""
