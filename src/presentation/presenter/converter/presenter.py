from __future__ import annotations

from src.application.contracts.converter_contract import IConverterController
from src.application.contracts.preferences_contract import IOutputFormatter
from src.application.dto import ConversionResultDTO, FormattingOutputDTO
from src.core.converter import NumericValidator
from src.presentation.formatters.clean_formatter import CleanFormatter
from src.presentation.presenter.converter.formatting import (
    build_output,
    prepare_source_input,
)
from src.presentation.presenter.converter.field_maps import (
    build_raw_outputs,
    empty_converter_text_map,
    normalize_source_input,
)
from src.presentation.presenter.converter.messages import build_validation_message
from src.presentation.presenter.converter.state import ConverterState


class ConverterPresenter:

    def __init__(
        self,
        controller: IConverterController,
        formatter: IOutputFormatter,
        initial_formatting: dict[str, FormattingOutputDTO],
    ):
        self._controller = controller
        self._output_formatter = formatter
        self._clean_formatter = CleanFormatter()
        self._formatting = dict(initial_formatting)
        self._state = ConverterState()

    @property
    def current_value(self) -> str:
        return self._state.current_value

    @property
    def current_from_type(self) -> str:
        return self._state.current_from_type

    @property
    def raw_inputs(self) -> dict[str, str]:
        return dict(self._state.raw_inputs)

    @property
    def last_output(self) -> dict[str, str]:
        return dict(self._state.last_output)

    @property
    def last_error_message(self) -> str | None:
        return self._state.last_error_message

    def on_user_input(
        self,
        from_type: str,
        raw_value: str,
    ) -> dict[str, str] | None:
        cleaned = normalize_source_input(
            from_type,
            self._clean_formatter.format(raw_value),
        )
        self._state.current_from_type = from_type
        self._state.raw_inputs[from_type] = cleaned

        if not cleaned:
            return self._state.reset_outputs()

        prepared = prepare_source_input(
            from_type,
            cleaned,
            self._formatting,
            self._output_formatter,
        )
        if not NumericValidator.validate(from_type, prepared):
            self._state.last_error_message = build_validation_message(from_type)
            return None

        self._state.current_value = cleaned
        try:
            result: ConversionResultDTO = self._controller.on_input_changed(
                from_type=from_type,
                value=prepared,
            )
        except ValueError as error:
            self._state.last_error_message = str(error)
            return None

        self._formatting = dict(result.formatting)
        self._state.raw_inputs = build_raw_outputs(from_type, cleaned, result.values)
        self._state.last_output = build_output(
            from_type,
            result.values,
            self._state.raw_inputs,
            self._formatting,
            self._output_formatter,
        )
        self._state.last_error_message = None
        return dict(self._state.last_output)

    def update_formatting(
        self,
        formatting: dict[str, FormattingOutputDTO],
    ) -> dict[str, str] | None:
        self._formatting = dict(formatting)
        if hasattr(self._controller, "set_formatting"):
            self._controller.set_formatting(formatting)

        if not self._state.current_value:
            self._state.last_output = empty_converter_text_map()
            return dict(self._state.last_output)

        return self.on_user_input(
            self._state.current_from_type,
            self._state.raw_inputs[self._state.current_from_type],
        )
