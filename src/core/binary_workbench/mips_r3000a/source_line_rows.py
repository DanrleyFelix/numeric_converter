from __future__ import annotations

from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_EMPTY_OFFSET as EMPTY_OFFSET,
    BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES,
)
from src.modules.contracts import CPUArchCodec
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.core.binary_workbench.mips_r3000a.preprocessor import raw_mips_instruction, strip_comment
from src.core.binary_workbench.mips_r3000a.pseudo_instructions import (
    expand_pseudo_instructions,
)

def build_source_line_rows(
    lines: list[str],
    offset_names: list[str],
    offset_bases: dict[str, str],
    codec: CPUArchCodec,
    start_offset: int = 0,
    labels: dict[str, str] | None = None,
    variables: dict[str, str] | None = None,
    equates: dict[str, str] | None = None,
    reject_invalid: bool = False,
) -> list[BinaryWorkbenchRowDTO] | None:
    expanded = expand_pseudo_instructions(lines)
    provisional_labels = _provisional_labels(expanded, start_offset)
    resolved_labels = provisional_labels if labels is None else {**labels, **provisional_labels}
    variables, equates = variables or {}, equates or {}
    rows = _build_rows(
        expanded,
        offset_names,
        offset_bases,
        codec,
        start_offset,
        resolved_labels,
        variables,
        equates,
        reject_invalid,
    )
    if rows is None or labels is not None:
        return rows
    for _ in range(2):
        updated_labels = labels_from_source_rows(rows, start_offset, codec.word_size)
        if updated_labels == resolved_labels:
            break
        resolved_labels = updated_labels
        rows = _build_rows(
            expanded,
            offset_names,
            offset_bases,
            codec,
            start_offset,
            resolved_labels,
            variables,
            equates,
            reject_invalid,
        )
        if rows is None:
            return None
    return rows


def _build_rows(
    lines: list[str],
    offset_names: list[str],
    offset_bases: dict[str, str],
    codec: CPUArchCodec,
    start_offset: int,
    labels: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
    reject_invalid: bool,
) -> list[BinaryWorkbenchRowDTO] | None:
    rows: list[BinaryWorkbenchRowDTO] = []
    offset = start_offset
    for line in lines:
        code = instruction_code(line)
        if not code:
            rows.append(empty_source_row(line, offset_names))
            continue
        raw_instruction = raw_mips_instruction(line, offset, labels, variables, equates)
        data = codec.assemble(raw_instruction, offset) if raw_instruction else None
        if data is None:
            if reject_invalid:
                return None
            rows.append(empty_source_row(line, offset_names))
            continue
        rows.append(
            BinaryWorkbenchRowDTO(
                offsets=offset_values(offset, offset_names, offset_bases),
                instruction=line.rstrip(),
                bytes_text=codec.bytes_text(data),
            )
        )
        offset += codec.word_size
    return rows


def _provisional_labels(lines: list[str], start_offset: int) -> dict[str, str]:
    labels: dict[str, str] = {}
    offset = start_offset
    for line in lines:
        label, code = split_label(strip_comment(line).strip())
        if label:
            labels[label] = f"0x{offset:08X}"
        if code:
            offset += ROW_BYTES
    return labels


def labels_from_source_rows(
    rows: list[BinaryWorkbenchRowDTO],
    start_offset: int = 0,
    word_size: int = ROW_BYTES,
) -> dict[str, str]:
    labels: dict[str, str] = {}
    offset = start_offset
    for row in rows:
        label, _ = split_label(strip_comment(row.instruction).strip())
        if label:
            labels[label] = f"0x{offset:08X}"
        if row.bytes_text:
            offset += word_size
    return labels


def instruction_code(text: str) -> str:
    return split_label(strip_comment(text).strip())[1]


def empty_source_row(text: str, offset_names: list[str]) -> BinaryWorkbenchRowDTO:
    return BinaryWorkbenchRowDTO(
        offsets={name: EMPTY_OFFSET for name in offset_names},
        instruction=text.rstrip(),
        bytes_text="",
    )


def offset_values(
    offset: int,
    offset_names: list[str],
    offset_bases: dict[str, str],
) -> dict[str, str]:
    return {
        name: f"0x{(0 if name == 'File' else int(offset_bases.get(name, '0x0'), 0)) + offset:08X}"
        for name in offset_names
    }


def split_label(text: str) -> tuple[str, str]:
    if ":" not in text:
        return "", text
    left, right = text.split(":", 1)
    candidate = left.strip()
    if candidate and left == left.rstrip() and " " not in candidate and "\t" not in candidate:
        return candidate, right.strip()
    return "", text
