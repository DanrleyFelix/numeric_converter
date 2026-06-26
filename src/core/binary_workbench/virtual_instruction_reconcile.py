from __future__ import annotations

from src.core.binary_workbench.mips_r3000a import build_source_line_rows
from src.core.binary_workbench.mips_r3000a.preprocessor import strip_comment
from src.core.binary_workbench.mips_r3000a.source_line_rows import (
    instruction_code,
)
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_EMPTY_OFFSET as EMPTY_OFFSET,
    BINARY_WORKBENCH_FILE_OFFSET_COLUMN as FILE_OFFSET,
)
from src.modules.contracts import CPUArchCodec
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


def reconcile_locked_virtual_instructions(
    lines: list[str],
    visible_rows: list[BinaryWorkbenchRowDTO],
    offset_names: list[str],
    offset_bases: dict[str, str],
    codec: CPUArchCodec,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
) -> list[BinaryWorkbenchRowDTO]:
    code_rows = [row for row in visible_rows if row.offsets.get(FILE_OFFSET) != EMPTY_OFFSET]
    rows: list[BinaryWorkbenchRowDTO] = []
    cursor = 0
    for index, line in enumerate(lines):
        if _inserted_line_before_current_row(lines, visible_rows, index, code_rows, cursor):
            rows.append(_comment_row(line, offset_names))
            continue
        if not instruction_code(line):
            if cursor < len(code_rows) and not _existing_comment_row(visible_rows, index):
                rows.append(_row_with_instruction(code_rows[cursor], line))
                cursor += 1
                continue
            rows.append(_comment_row(line, offset_names))
            continue
        if _current_row_matches(line, code_rows, cursor):
            base = code_rows[cursor]
            rows.append(_assembled_or_previous(line, base, offset_names, offset_bases, codec, labels, variables, equates))
            cursor += 1
            continue
        match = _matching_later_row(line, code_rows, cursor)
        if match is not None:
            rows.extend(_cleared_rows(code_rows[cursor:match]))
            rows.append(_row_with_instruction(code_rows[match], line))
            cursor = match + 1
            continue
        if _existing_comment_row(visible_rows, index):
            rows.append(_comment_row(line, offset_names))
            continue
        if cursor >= len(code_rows):
            rows.append(_comment_row(line, offset_names))
            continue
        base = code_rows[cursor]
        rows.append(_assembled_or_previous(line, base, offset_names, offset_bases, codec, labels, variables, equates))
        cursor += 1
    rows.extend(code_rows[cursor:])
    return rows


def _inserted_line_before_current_row(
    lines: list[str],
    visible_rows: list[BinaryWorkbenchRowDTO],
    index: int,
    rows: list[BinaryWorkbenchRowDTO],
    cursor: int,
) -> bool:
    return (
        len(lines) > len(visible_rows)
        and cursor < len(rows)
        and not _current_row_matches(lines[index], rows, cursor)
        and _later_line_matches_row(lines, index + 1, rows[cursor])
    )


def _later_line_matches_row(
    lines: list[str],
    start: int,
    row: BinaryWorkbenchRowDTO,
) -> bool:
    return any(_code_key(line) == _code_key(row.instruction) for line in lines[start:])


def _current_row_matches(
    line: str,
    rows: list[BinaryWorkbenchRowDTO],
    index: int,
) -> bool:
    return index < len(rows) and _code_key(rows[index].instruction) == _code_key(line)


def _matching_later_row(
    line: str,
    rows: list[BinaryWorkbenchRowDTO],
    start: int,
) -> int | None:
    line_key = _code_key(line)
    return next(
        (
            index
            for index in range(start + 1, len(rows))
            if _code_key(rows[index].instruction) == line_key
        ),
        None,
    )


def _assembled_or_previous(
    line: str,
    base: BinaryWorkbenchRowDTO,
    offset_names: list[str],
    offset_bases: dict[str, str],
    codec: CPUArchCodec,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
) -> BinaryWorkbenchRowDTO:
    offset = int(base.offsets.get(FILE_OFFSET, "0x0"), 16)
    rows = build_source_line_rows(
        [line],
        offset_names,
        offset_bases,
        codec,
        offset,
        labels,
        variables,
        equates,
        True,
    )
    if rows and rows[0].bytes_text:
        return BinaryWorkbenchRowDTO(
            offsets=base.offsets,
            instruction=rows[0].instruction,
            bytes_text=rows[0].bytes_text,
        )
    return _row_with_instruction(base, line)


def _row_with_instruction(
    row: BinaryWorkbenchRowDTO,
    instruction: str,
) -> BinaryWorkbenchRowDTO:
    return BinaryWorkbenchRowDTO(
        offsets=row.offsets,
        instruction=instruction.rstrip(),
        bytes_text=row.bytes_text,
    )


def _comment_row(line: str, offset_names: list[str]) -> BinaryWorkbenchRowDTO:
    return BinaryWorkbenchRowDTO(
        offsets={name: EMPTY_OFFSET for name in offset_names},
        instruction=line.rstrip(),
        bytes_text="",
    )


def _cleared_rows(rows: list[BinaryWorkbenchRowDTO]) -> list[BinaryWorkbenchRowDTO]:
    return [_row_with_instruction(row, "") for row in rows]


def _existing_comment_row(rows: list[BinaryWorkbenchRowDTO], index: int) -> bool:
    return index < len(rows) and rows[index].offsets.get(FILE_OFFSET) == EMPTY_OFFSET


def _code_key(text: str) -> str:
    return "".join(strip_comment(text).split()).casefold()
