from src.presentation.ui.components.help_window.pages.binary_workbench.environment import PAGE as ENVIRONMENT_PAGE
from src.presentation.ui.components.help_window.pages.binary_workbench.editor_helpers import PAGE as EDITOR_HELPERS_PAGE
from src.presentation.ui.components.help_window.pages.binary_workbench.file import PAGE as FILE_PAGE
from src.presentation.ui.components.help_window.pages.binary_workbench.internal_files import PAGE as INTERNAL_FILES_PAGE
from src.presentation.ui.components.help_window.pages.binary_workbench.main_window import PAGE as MAIN_WINDOW_PAGE
from src.presentation.ui.components.help_window.pages.binary_workbench.preferences import PAGE as PREFERENCES_PAGE
from src.presentation.ui.components.help_window.pages.binary_workbench.search import PAGE as SEARCH_PAGE
from src.presentation.ui.components.help_window.pages.binary_workbench.shortcuts import PAGE as SHORTCUTS_PAGE
from src.presentation.ui.components.help_window.pages.binary_workbench.versions import PAGE as VERSIONS_PAGE


BINARY_WORKBENCH_HELP_PAGES = [
    MAIN_WINDOW_PAGE,
    FILE_PAGE,
    VERSIONS_PAGE,
    INTERNAL_FILES_PAGE,
    ENVIRONMENT_PAGE,
    PREFERENCES_PAGE,
    SEARCH_PAGE,
    EDITOR_HELPERS_PAGE,
    SHORTCUTS_PAGE,
]


__all__ = ["BINARY_WORKBENCH_HELP_PAGES"]
