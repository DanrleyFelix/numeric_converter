from __future__ import annotations

from pathlib import Path

from src.core.debugger.imports.source import DebuggerAssemblySource
from src.core.debugger.models.session import DebuggerError, DebuggerErrorCode
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_TAB_KIND
from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.editor.page import (
    BinaryWorkbenchEditorPage,
)
from src.presentation.ui.components.binary_workbench.tabs.tab_context_factory import (
    create_assembly_tab,
)


class TabDebuggerSourceMixin:
    """Expose workspace-aware assembly sources without opening or switching tabs."""

    def debugger_current_source(self) -> DebuggerAssemblySource:
        """Return the fresh current `.asm` source used to start a debug session."""

        context = self.current_context()
        if (
            context is None
            or context.kind != BINARY_WORKBENCH_TAB_KIND.ASSEMBLY
            or not context.source_path
        ):
            raise DebuggerError(
                DebuggerErrorCode.IMPORT_FAILED,
                "Debugger requires a saved assembly file in the current tab.",
            )
        return _source_from_context(context)

    def debugger_source_for(self, path: Path) -> DebuggerAssemblySource:
        """Load one assembly source with its matching workspace environment."""

        target = path.resolve()
        for index, context in enumerate(self._state.tabs):
            if not context.source_path or Path(context.source_path).resolve() != target:
                continue
            page = self.widget(index)
            if isinstance(page, BinaryWorkbenchEditorPage):
                fresh = self._fresh_context_at(index)
                if fresh is not None:
                    return _source_from_context(fresh)
            return _source_from_context(self._persisted_import_context(target, context))
        return _source_from_context(self._persisted_import_context(target))

    def _persisted_import_context(
        self,
        target: Path,
        known: BinaryWorkbenchTabContextDTO | None = None,
    ) -> BinaryWorkbenchTabContextDTO:
        """Load the saved active version without opening or activating its tab."""

        if not target.is_file():
            raise DebuggerError(
                DebuggerErrorCode.IMPORT_FAILED,
                f"Debugger import does not exist: {target}",
            )
        baseline = create_assembly_tab(
            self._state,
            target,
            self._preferences,
            derive_rows=False,
        )
        context = _context_with_source_rows(known, baseline)
        linked = Path(known.workspace_path) if known and known.workspace_path else None
        preferred = linked or self._controller.preferred_workspace(
            self._program_context,
            target,
        )
        manifest = self._workspace_repository.find_for_source(target, preferred)
        if manifest is not None:
            context = self._workspace_repository.load_tab_workspace(context, manifest)
            context = self._with_symbol_offsets(context)
        context = self._context_with_global_symbols(context)
        return context


def _source_from_context(
    context: BinaryWorkbenchTabContextDTO,
) -> DebuggerAssemblySource:
    """Convert one tab context into the core assembly-source contract."""

    if not context.source_path:
        raise DebuggerError(
            DebuggerErrorCode.IMPORT_FAILED,
            "Debugger source has no saved path.",
        )
    return DebuggerAssemblySource(
        Path(context.source_path),
        context.workspace_path,
        tuple(row.instruction for row in context.rows),
        context.cpu_arch,
        dict(context.labels),
        dict(context.variables),
        dict(context.equates),
    )


def _context_with_source_rows(
    known: BinaryWorkbenchTabContextDTO | None,
    baseline: BinaryWorkbenchTabContextDTO,
) -> BinaryWorkbenchTabContextDTO:
    """Seed an inactive context from disk while preserving its stable identity."""

    if known is None:
        return baseline
    return BinaryWorkbenchTabContextDTO(
        **{
            **known.__dict__,
            "source_path": baseline.source_path,
            "display_name": baseline.display_name,
            "original_rows": baseline.original_rows,
            "rows": baseline.rows,
            "file_size": baseline.file_size,
            "original_file_size": baseline.original_file_size,
        }
    )
