from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.core.debugger.models.session import DebuggerError
from src.core.debugger.session.factory import create_debugger_session
from src.presentation.repository.debugger_window.repository import (
    DebuggerWindowStateRepository,
)
from src.presentation.ui.components.debugger.constants.layout import (
    DEBUGGER_STATE_FILENAME,
)
from src.presentation.ui.components.debugger.constants.texts import (
    DEBUGGER_ACTIONS,
    DEBUGGER_START_REQUIRED,
)
from src.presentation.ui.components.debugger.window import DebuggerWindow
from src.presentation.ui.helpers.window_geometry import ensure_window_on_available_screen


class BinaryWorkbenchDebuggerMixin:
    """Open and route shared debugger actions by current workspace."""

    def _initialize_debugger_support(self) -> None:
        """Create independent window storage and geometry persistence."""

        self._debugger_windows: dict[str, DebuggerWindow] = {}
        state_path = self.tabs._workspace_repository.directory.parent / DEBUGGER_STATE_FILENAME
        self._debugger_state_repository = DebuggerWindowStateRepository(state_path)

    def _connect_debugger_actions(self) -> None:
        """Connect each shared QAction to the active debugger-aware target."""

        for name, _text, _shortcut in DEBUGGER_ACTIONS:
            action = getattr(self.toolbar.debugger_actions, name)
            action.triggered.connect(
                lambda _checked=False, operation=name: self._route_debugger_action(operation)
            )
        self.addActions(list(self.toolbar.debugger_actions.all()))

    def _route_debugger_action(self, operation: str) -> None:
        """Route shortcuts to the active debugger or current workspace session."""

        active = QApplication.activeWindow()
        if isinstance(active, DebuggerWindow) and active in self._debugger_windows.values():
            active.perform(operation)
            return
        window = self._current_debugger_window()
        if operation == "run":
            barrier = self.tabs.ensure_current_consistent("debugger")
            if not barrier.success:
                self._show_status(barrier.error or "Unable to prepare the debugger source.", 0, True)
                return
            if window is None:
                self._open_debugger_window()
            else:
                refreshed = self._open_debugger_window(refresh_existing=True)
                if refreshed is not None:
                    self._show_debugger_window(refreshed)
                    refreshed.perform("run")
            return
        if window is None:
            self._show_warning_status(DEBUGGER_START_REQUIRED)
            return
        self._show_debugger_window(window)
        window.perform(operation)

    def _open_debugger_window(self, refresh_existing: bool = False) -> DebuggerWindow | None:
        """Build the complete session transactionally before showing a window."""

        try:
            source = self.tabs.debugger_current_source()
            key = self._debugger_key(source.workspace, source.path)
            existing = self._debugger_windows.get(key)
            if existing is not None and not refresh_existing:
                return existing
            bundle = create_debugger_session(source, self.tabs.debugger_source_for)
            window = DebuggerWindow(
                bundle,
                self.toolbar.debugger_actions,
                self._debugger_state_repository,
                key,
            )
        except DebuggerError as error:
            self._show_status(error.message, 0, True)
            return None
        except Exception as error:
            self._show_status(str(error) or "Unable to create the debugger session.", 0, True)
            return None
        if existing is not None and not existing.close():
            window.deleteLater()
            return existing
        if existing is not None:
            self._debugger_windows.pop(key, None)
        window.setAttribute(Qt.WA_DeleteOnClose, True)
        window.setWindowIcon(self.windowIcon())
        window.statusError.connect(lambda message: self._show_status(message, 0, True))
        window.destroyed.connect(
            lambda _object=None, item=key, target=window: self._discard_debugger_window(
                item, target
            )
        )
        self._debugger_windows[key] = window
        self._show_debugger_window(window)
        return window

    def _current_debugger_window(self) -> DebuggerWindow | None:
        """Return the preserved session associated with the current source."""

        try:
            source = self.tabs.debugger_current_source()
        except DebuggerError:
            return None
        return self._debugger_windows.get(self._debugger_key(source.workspace, source.path))

    def _show_debugger_window(self, window: DebuggerWindow) -> None:
        """Restore a debugger window to an available monitor and activate it."""

        ensure_window_on_available_screen(window, self)
        window.show()
        ensure_window_on_available_screen(window, self)
        window.raise_()
        window.activateWindow()

    def _discard_debugger_window(self, key: str, window: DebuggerWindow) -> None:
        """Forget only the destroyed instance currently bound to a workspace."""

        if self._debugger_windows.get(key) is window:
            self._debugger_windows.pop(key, None)

    def _close_debugger_windows(self) -> bool:
        """Close every child session before the Binary Workbench exits."""

        return all(window.close() for window in tuple(self._debugger_windows.values()))

    @staticmethod
    def _debugger_key(workspace: str | None, source_path: Path) -> str:
        """Return one normalized persistence and session key."""

        return str(Path(workspace).resolve() if workspace else source_path.parent.resolve()).casefold()
