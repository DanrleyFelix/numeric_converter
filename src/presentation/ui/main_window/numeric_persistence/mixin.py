from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.presentation.ui.main_window.window import MainWindow


class MainWindowNumericPersistenceMixin:
    """Isolate Numeric autosave and route other domains explicitly."""

    def _numeric_revision_token(self: MainWindow) -> tuple[int, int]:
        """Return the current source and semantic Numeric revisions."""

        document = self.body.command_panel.editor.document()
        return document.revision(), self._numeric_semantic_revision

    def _numeric_autosave_snapshot(self: MainWindow):
        """Capture only the Numeric application context when the timer is due."""

        return self._collect_context(), self._numeric_revision_token()

    def _mark_numeric_dirty(self: MainWindow, kind: str, *, semantic: bool = True) -> None:
        """Mark one Numeric domain without collecting or saving another domain."""

        if not self._loaded:
            return
        if semantic:
            self._numeric_semantic_revision += 1
        revision = self._numeric_revision_token()
        self._numeric_autosave.mark_dirty(kind, revision)

    def _on_command_document_modified(self: MainWindow, modified: bool) -> None:
        """Arm autosave once when the command document becomes modified."""

        if modified:
            self._mark_numeric_dirty("active-line", semantic=False)

    def _handle_numeric_autosave_saved(self: MainWindow, result: object) -> None:
        """Reset Qt's dirty transition only for the revision that was saved."""

        revision = getattr(result, "revision", None)
        if revision == self._numeric_revision_token():
            self.body.command_panel.editor.document().setModified(False)

    def _persist_numeric_flags(self: MainWindow) -> None:
        """Persist Numeric UI preferences without touching Binary state."""

        self._preferences_service.update_numeric_flags(
            self.key_panel.isVisible(),
            self._auto_convert_enabled,
        )
