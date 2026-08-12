from pathlib import Path

from src.core.debugger.imports.source import DebuggerAssemblySource
from src.core.debugger.models.session import DebuggerSessionState
from src.core.debugger.session.factory import create_debugger_session
from src.modules.application_dtos import ProgramContextDTO
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
)
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchPreferencesDTO,
    BinaryWorkbenchRowDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchVersionDTO,
)
from src.presentation.repository.binary_workbench_workspace import (
    BinaryWorkbenchWorkspaceRepository,
)
from src.presentation.ui.components.binary_workbench.tabs.debugger.source_provider import (
    TabDebuggerSourceMixin,
)


class _Controller:
    def __init__(self, preferred: Path | None) -> None:
        self.preferred = preferred

    def preferred_workspace(self, _context, _source: Path) -> Path | None:
        return self.preferred


class _SourceHost(TabDebuggerSourceMixin):
    """Exercise import loading without creating or activating editor pages."""

    def __init__(self, state, repository, preferred: Path | None) -> None:
        self._state = state
        self._workspace_repository = repository
        self._controller = _Controller(preferred)
        self._program_context = ProgramContextDTO()
        self._preferences = BinaryWorkbenchPreferencesDTO()

    def widget(self, _index: int):
        return None

    def _with_symbol_offsets(self, context):
        return context

    def _context_with_global_symbols(self, context):
        return context


def _saved_assembly_workspace(
    tmp_path: Path,
    active_instructions: tuple[str, ...] = ("addiu $v0, $zero, 42",),
):
    source = tmp_path / "library.asm"
    source.write_text("nop\n", encoding="utf-8")
    repository = BinaryWorkbenchWorkspaceRepository(tmp_path)
    active_rows = [BinaryWorkbenchRowDTO(instruction=text) for text in active_instructions]
    context = BinaryWorkbenchTabContextDTO(
        tab_id="library",
        kind="assembly",
        display_name=source.name,
        source_path=str(source),
        rows=[BinaryWorkbenchRowDTO(instruction="nop")],
        original_rows=[BinaryWorkbenchRowDTO(instruction="nop")],
        versions=[BinaryWorkbenchVersionDTO("active", rows=active_rows)],
        active_version_name="active",
    )
    saved = repository.save_tab_workspace(
        context,
        repository.directory / "library_workspace_manifest.json",
    )
    return source, repository, saved


def test_closed_import_uses_its_persisted_active_version(tmp_path: Path):
    source, repository, saved = _saved_assembly_workspace(tmp_path)
    state = BinaryWorkbenchStateDTO()
    host = _SourceHost(state, repository, Path(saved.workspace_path or ""))

    imported = host.debugger_source_for(source)

    assert imported.lines == ("addiu $v0, $zero, 42",)
    assert state.tabs == []


def test_inactive_unmaterialized_import_does_not_use_stale_rows(tmp_path: Path):
    source, repository, saved = _saved_assembly_workspace(tmp_path)
    inactive = BinaryWorkbenchTabContextDTO(
        **{
            **saved.__dict__,
            "rows": [BinaryWorkbenchRowDTO(instruction="nop")],
        }
    )
    state = BinaryWorkbenchStateDTO(tabs=[inactive])
    host = _SourceHost(state, repository, None)

    imported = host.debugger_source_for(source)

    assert imported.lines == ("addiu $v0, $zero, 42",)
    assert state.tabs[0].rows[0].instruction == "nop"


def test_closed_active_version_is_assembled_and_executed_without_a_tab(tmp_path: Path):
    """Exercise the complete import path without materializing an editor page."""

    library, repository, saved = _saved_assembly_workspace(
        tmp_path,
        ("addiu $v0, $zero, 42", "jr $ra", "nop"),
    )
    main_path = tmp_path / "main.asm"
    lines = (
        "* virtual_memory_range 0x80000000 0x801DFFFF",
        "* import current_file 0x8000F800",
        "* import library.asm 0x801D9200",
        "* define $pc 0x8000F800",
        "* define $sp 0x801DFFF0",
        "jal 0x801D9200",
        "nop",
        "nop",
    )
    main_path.write_text("\n".join(lines), encoding="utf-8")
    main = DebuggerAssemblySource(
        main_path,
        None,
        lines,
        BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
        {},
        {},
        {},
    )
    state = BinaryWorkbenchStateDTO()
    host = _SourceHost(state, repository, Path(saved.workspace_path or ""))

    bundle = create_debugger_session(main, host.debugger_source_for)
    imported = next(item for item in bundle.imports if item.path == library)
    bundle.debugger.run(limit=20)

    assert imported.address == 0x801D9200
    assert imported.size == 12
    assert bundle.debugger.registers.read("v0") == 42
    assert bundle.debugger.state == DebuggerSessionState.STOPPED, "\n".join(
        f"{event.level}: {event.message}" for event in bundle.debugger.events
    )
    assert state.tabs == []
