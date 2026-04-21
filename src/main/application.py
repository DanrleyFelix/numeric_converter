from pathlib import Path

from src.application.services.formating_preferences import FormattingPreferencesService
from src.application.services.workspace_state_service import WorkspaceStateService
from src.application.use_cases.converter_use_case import ConverterUseCase
from src.application.use_cases.evaluator_use_case import EvaluatorUseCase
from src.controllers.cmd_window_controller import CommandWindowController
from src.controllers.converter_controller import ConverterController
from src.core.command_window.evaluator.evaluator import Evaluator
from src.core.command_window.validator.validator import ExpressionValidator
from src.presentation.formatters.converter_output import OutputFormatter
from src.presentation.presenter.cmd_window_presenter import CommandWindowPresenter
from src.presentation.presenter.converter_presenter import ConverterPresenter
from src.presentation.repository.preferences_formatter import FormattingPreferencesRepository
from src.presentation.repository.workspace_state import (
    ApplicationContextRepository,
    CommandLogRepository,
    WorkspaceStateRepository,
)
from src.presentation.ui.main_window import MainWindow


def create_main_window(root: Path | None = None) -> MainWindow:
    root = root or Path(__file__).resolve().parents[2]

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
        log_repository=CommandLogRepository(root),
        workspace_repository=WorkspaceStateRepository(root),
    )

    return MainWindow(
        converter_presenter=converter_presenter,
        command_presenter=command_presenter,
        state_service=state_service,
        preferences_service=preferences_service,
    )
