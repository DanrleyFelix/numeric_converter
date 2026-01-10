from typing import Optional, Any

from src.application.contracts.preferences_contract import IOutputFormatter
from src.application.contracts.converter_contract import IConverterController
from src.application.dto import ConversionResultDTO, FormattingOutputDTO
from src.presentation.formatters.clean_formatter import CleanFormatter
from src.core.converter import NumericValidator


class ConverterPresenter:

    def __init__(
        self,
        controller: IConverterController,
        formatter: IOutputFormatter):
        
        self._controller = controller
        self._output_formatter = formatter
        self._clean_formatter = CleanFormatter()

        self._current_value: str = ""

    @property
    def current_value(self) -> str:
        return self._current_value

    def on_user_input(
        self,
        from_type: str,
        raw_value: str) -> Optional[dict[str, str]]:

        cleaned = self._clean_formatter.format(raw_value)
        if not NumericValidator.validate(from_type, cleaned):
            return None
        self._current_value = cleaned
        result: ConversionResultDTO = self._controller.on_input_changed(
            from_type=from_type,
            value=cleaned)

        values: dict[str, Any] = result.values
        formatters: dict[str, FormattingOutputDTO] = result.formatting

        output: dict[str, str] = {}

        for kind, value in values.items():
            fmt = formatters[kind]
            if kind == "dec":
                output[kind] = self._output_formatter.format_decimal(value, fmt)
            elif kind == "bin":
                output[kind] = self._output_formatter.format_binary(value, fmt)
            elif kind == "hex":
                output[kind] = self._output_formatter.format_hex(value, fmt)

        return output
