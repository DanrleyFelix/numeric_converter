from typing import Optional, Any

from src.application.contracts.preferences_contract import IOutputFormatter
from src.application.contracts.converter_contract import IConverterController
from src.application.dto import ConversionResult, FormattingOutput


class ConverterView:

    def __init__(self, controller: IConverterController, formatter: IOutputFormatter):
        self.controller = controller
        self.output_formatter = formatter

    def on_user_input(self, from_type: str, raw_value: str) -> Optional[dict[str, str]]:

        result: ConversionResult | None = self.controller.on_input_changed(
            from_type=from_type,
            raw_value=raw_value)

        if result is None:
            return None

        values: dict[str, Any] = result["values"]
        formatters: dict[str, FormattingOutput] = result["formatter"]
        output: dict[str, str] = {}

        for kind, value in values.items():
            fmt = formatters[kind]
            if kind == "dec":
                output[kind] = self.output_formatter.format_decimal(value, fmt)
            elif kind == "bin":
                output[kind] = self.output_formatter.format_binary(value, fmt)
            elif kind == "hex":
                output[kind] = self.output_formatter.format_hex(value, fmt)
        return output
