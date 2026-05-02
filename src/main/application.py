from pathlib import Path

from src.controllers.cmd_window_controller import CommandWindowController
from src.controllers.converter_controller import ConverterController
from src.core.command_window.evaluator.evaluator import Evaluator
from src.core.command_window.validator.validator import ExpressionValidator
from src.modules.services import FormattingPreferencesService, WorkspaceStateService
from src.modules.use_cases import ConverterUseCase, EvaluatorUseCase
from src.presentation.formatters.converter_output import OutputFormatter
from src.presentation.presenter.cmd_window_presenter import CommandWindowPresenter
from src.presentation.presenter.converter_presenter import ConverterPresenter
from src.presentation.repository.preferences_formatter import FormattingPreferencesRepository
from src.presentation.repository.workspace_state import (
    ApplicationContextRepository,
    WorkspaceStateRepository,
)
from src.presentation.ui.main_window import MainWindow
from src.main.runtime_root import resolve_application_root


def create_main_window(root: Path | None = None) -> MainWindow:
    root = root or resolve_application_root()

    preferences_service = FormattingPreferencesService(
        FormattingPreferencesRepository(root)
    )
    formatter = OutputFormatter()

    converter_presenter = ConverterPresenter(
        controller=ConverterController(
            use_case=ConverterUseCase(),
            formatting=preferences_service.get_format(),
        ),
        formatter=formatter,
        initial_formatting=preferences_service.get_format(),
    )
    command_presenter = CommandWindowPresenter(
        controller=CommandWindowController(
            validator=ExpressionValidator,
            evaluator_use_case=EvaluatorUseCase(Evaluator()),
        ),
        formatter=formatter,
    )
    state_service = WorkspaceStateService(
        context_repository=ApplicationContextRepository(root),
        workspace_repository=WorkspaceStateRepository(root),
    )

    return MainWindow(
        converter_presenter=converter_presenter,
        command_presenter=command_presenter,
        state_service=state_service,
        preferences_service=preferences_service,
    )
