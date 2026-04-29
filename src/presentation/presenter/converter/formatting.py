from __future__ import annotations

from typing import Any

from src.application.contracts.preferences_contract import IOutputFormatter
from src.application.dto import FormattingOutputDTO
from src.presentation.presenter.converter.constants import CONVERTER_TYPE


def prepare_source_input(
    from_type: str,
    value: str,
    formatting: dict[str, FormattingOutputDTO],
    formatter: IOutputFormatter,
) -> str:
    source_format = formatting.get(from_type, FormattingOutputDTO())
    if from_type == CONVERTER_TYPE.DECIMAL:
        return formatter.prepare_decimal_input(value, source_format)
    if from_type == CONVERTER_TYPE.BINARY:
        return formatter.prepare_binary_input(value, source_format)
    return formatter.prepare_hex_input(value, source_format)


def format_source_input(
    from_type: str,
    value: str,
    formatting: dict[str, FormattingOutputDTO],
    formatter: IOutputFormatter,
) -> str:
    source_format = formatting.get(from_type)
    if from_type == CONVERTER_TYPE.DECIMAL:
        return formatter.format_decimal_input(value, source_format)
    if from_type == CONVERTER_TYPE.BINARY:
        return formatter.format_binary(value, source_format)
    return formatter.format_hex_input(value, source_format)


def build_output(
    from_type: str,
    values: dict[str, Any],
    raw_inputs: dict[str, str],
    formatting: dict[str, FormattingOutputDTO],
    formatter: IOutputFormatter,
) -> dict[str, str]:
    output: dict[str, str] = {}
    for kind, value in values.items():
        if kind == from_type:
            output[kind] = format_source_input(from_type, raw_inputs[kind], formatting, formatter)
        elif kind == CONVERTER_TYPE.DECIMAL:
            output[kind] = formatter.format_decimal(value, formatting[kind])
        elif kind == CONVERTER_TYPE.BINARY:
            output[kind] = formatter.format_binary(value, formatting[kind])
        elif kind in (CONVERTER_TYPE.HEX_BE, CONVERTER_TYPE.HEX_LE):
            output[kind] = formatter.format_hex(value, formatting[kind])
    return output
