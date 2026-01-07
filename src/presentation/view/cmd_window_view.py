from src.application.contracts.cmd_window_contract import ICommandWindowController
from src.application.contracts.preferences_contract import IOutputFormatter
from src.modules.utils import COLOR


class CommandWindowView:
    def __init__(self, formatter: IOutputFormatter,
                  controller: ICommandWindowController):
        self.controller = controller
        self.formatter = formatter

    def handle_typing(self, text: str) -> tuple[list[str], COLOR]:
        try:
            state = self.controller.on_input_changed(text)
        except Exception as e:
            return [text, str(e)], COLOR.FAILED
        if not state:
            return [text], COLOR.INCOMPLETE
        return [text], COLOR.SUCCESS

    def handle_enter(self, text: str) -> tuple[list[str], COLOR]:
        try:
            state = self.controller.on_input_changed(text)
            result = self.controller.on_confirm(state)
        except Exception as e:
            return [text, str(e)], COLOR.FAILED
        if result is None:
            return [text, "Incompleted expression!"], COLOR.INCOMPLETE
        formatted_result = self.formatter.format_decimal(result)
        return [formatted_result], COLOR.SUCCESS
