from typing import Any, Optional

from src.application.contracts.converter_contract import IConverterController
from src.application.contracts.preferences_contract import IOutputFormatter
from src.application.dto import ConversionResultDTO, FormattingOutputDTO
from src.core.converter import MAX_BYTE_LENGTH, NumericValidator
from src.presentation.formatters.clean_formatter import CleanFormatter


class ConverterPresenter:

    def __init__(
        self,
        controller: IConverterController,
        formatter: IOutputFormatter,
    ):

        self._controller = controller
        self._output_formatter = formatter
        self._clean_formatter = CleanFormatter()

        self._current_value: str = ""
        self._current_from_type: str = "decimal"
        self._raw_inputs: dict[str, str] = {
            "decimal": "",
            "binary": "",
            "hexBE": "",
            "hexLE": "",
        }
        self._last_output: dict[str, str] = {
            "decimal": "",
            "binary": "",
            "hexBE": "",
            "hexLE": "",
        }
        self._last_error_message: str | None = None

    @property
    def current_value(self) -> str:
        return self._current_value

    @property
    def current_from_type(self) -> str:
        return self._current_from_type

    @property
    def raw_inputs(self) -> dict[str, str]:
        return dict(self._raw_inputs)

    @property
    def last_output(self) -> dict[str, str]:
        return dict(self._last_output)

    @property
    def last_error_message(self) -> str | None:
        return self._last_error_message

    def on_user_input(
        self,
        from_type: str,
        raw_value: str,
    ) -> Optional[dict[str, str]]:

        cleaned = self._normalize_source_input(
            from_type,
            self._clean_formatter.format(raw_value),
        )
        self._current_from_type = from_type
        self._raw_inputs[from_type] = cleaned

        if not cleaned:
            self._current_value = ""
            self._last_error_message = None
            self._raw_inputs = {
                "decimal": "",
                "binary": "",
                "hexBE": "",
                "hexLE": "",
            }
            self._last_output = {
                "decimal": "",
                "binary": "",
                "hexBE": "",
                "hexLE": "",
            }
            return dict(self._last_output)

        if self._is_partial_input(from_type, cleaned):
            self._current_value = cleaned
            self._last_error_message = None
            self._last_output = self._build_partial_output(from_type, cleaned)
            return dict(self._last_output)

        if not NumericValidator.validate(from_type, cleaned):
            self._last_error_message = self._build_validation_message(from_type, cleaned)
            return None

        self._current_value = cleaned
        try:
            result: ConversionResultDTO = self._controller.on_input_changed(
                from_type=from_type,
                value=cleaned,
            )
        except ValueError as error:
            self._last_error_message = str(error)
            return None

        values: dict[str, Any] = result.values
        formatters: dict[str, FormattingOutputDTO] = result.formatting

        raw_outputs = {
            "decimal": cleaned if from_type == "decimal" else str(values["decimal"]),
            "binary": cleaned if from_type == "binary" else str(values["binary"]),
            "hexBE": cleaned.upper() if from_type == "hexBE" else values["hexBE"].hex().upper(),
            "hexLE": cleaned.upper() if from_type == "hexLE" else values["hexLE"].hex().upper(),
        }
        self._raw_inputs = raw_outputs

        output: dict[str, str] = {}

        for kind, value in values.items():
            formatter = formatters[kind]
            if kind == from_type:
                output[kind] = self._format_input(kind, raw_outputs[kind], formatter)
            elif kind == "decimal":
                output[kind] = self._output_formatter.format_decimal(value, formatter)
            elif kind == "binary":
                output[kind] = self._output_formatter.format_binary(value, formatter)
            elif kind in ("hexBE", "hexLE"):
                output[kind] = self._output_formatter.format_hex(value, formatter)

        self._last_error_message = None
        self._last_output = output
        return dict(output)

    def update_formatting(
        self,
        formatting: dict[str, FormattingOutputDTO],
    ) -> Optional[dict[str, str]]:
        if hasattr(self._controller, "set_formatting"):
            self._controller.set_formatting(formatting)

        if not self._current_value:
            self._last_output = {
                "decimal": "",
                "binary": "",
                "hexBE": "",
                "hexLE": "",
            }
            return dict(self._last_output)

        return self.on_user_input(
            self._current_from_type,
            self._raw_inputs[self._current_from_type],
        )

    def _build_partial_output(self, from_type: str, cleaned: str) -> dict[str, str]:
        output = {
            "decimal": "",
            "binary": "",
            "hexBE": "",
            "hexLE": "",
        }
        output[from_type] = self._format_input(from_type, cleaned)
        return output

    def _format_input(
        self,
        from_type: str,
        value: str,
        formatter: FormattingOutputDTO | None = None,
    ) -> str:
        if from_type == "decimal":
            return self._output_formatter.format_decimal_input(value, formatter)
        if from_type == "binary":
            return self._output_formatter.format_binary(value, formatter)
        return self._output_formatter.format_hex_input(value, formatter)

    def _is_partial_input(self, from_type: str, cleaned: str) -> bool:
        return from_type in ("hexBE", "hexLE") and len(cleaned) % 2 == 1

    def _normalize_source_input(self, from_type: str, value: str) -> str:
        if from_type in ("hexBE", "hexLE"):
            return value.upper()
        return value

    def _build_validation_message(self, from_type: str, cleaned: str) -> str:
        if from_type == "decimal":
            return f"Decimal aceita apenas dígitos e até {MAX_BYTE_LENGTH} bytes."
        if from_type == "binary":
            return f"Binary aceita apenas 0 e 1 e até {MAX_BYTE_LENGTH * 8} bits."
        if len(cleaned) % 2 != 0:
            return "Hex precisa ter quantidade par de dígitos."
        return f"Hex aceita até {MAX_BYTE_LENGTH} bytes."
