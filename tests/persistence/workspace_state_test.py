from pathlib import Path

from src.application.dto.application_state import (
    ApplicationContextDTO,
    CommandContextDTO,
    ConverterStateDTO,
    WorkspaceStateDTO,
)
from src.application.dto.command_entry import CommandEntryDTO
from src.presentation.repository.workspace_state import (
    ApplicationContextRepository,
    WorkspaceStateRepository,
)


def test_application_context_roundtrip(tmp_path: Path):
    repository = ApplicationContextRepository(tmp_path)
    context = ApplicationContextDTO(
        converter=ConverterStateDTO(
            from_type="hexBE",
            fields={
                "decimal": "255",
                "binary": "11111111",
                "hexBE": "FF",
                "hexLE": "FF",
            },
            message=None,
        ),
        command=CommandContextDTO(
            active_line="a + 1",
            history=[CommandEntryDTO(input="a = 1", output="1")],
            instructions=["a = 1"],
            variables={"ANS": 1, "a": 1},
        ),
        key_panel_visible=False,
    )

    saved_path = repository.save(context, Path("session_one"))
    loaded = repository.load(saved_path)

    assert saved_path == repository.directory / "session_one.json"
    assert loaded == context


def test_workspace_state_roundtrip_saves_context(tmp_path: Path):
    repository = WorkspaceStateRepository(tmp_path)
    workspace = WorkspaceStateDTO(
        context=ApplicationContextDTO(
            converter=ConverterStateDTO(
                from_type="decimal",
                fields={
                    "decimal": "42",
                    "binary": "101010",
                    "hexBE": "2A",
                    "hexLE": "2A",
                },
                message=None,
            ),
            command=CommandContextDTO(
                active_line="answer",
                history=[CommandEntryDTO(input="answer=42", output="42")],
                instructions=["answer=42"],
                variables={"ANS": 42, "answer": 42},
            ),
            key_panel_visible=True,
        ),
    )

    saved_path = repository.save(workspace, Path("full_workspace"))
    loaded = repository.load(saved_path)

    assert saved_path == repository.directory / "full_workspace.json"
    assert loaded == workspace
