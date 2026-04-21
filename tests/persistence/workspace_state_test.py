from pathlib import Path

from src.application.dto.application_state import (
    ApplicationContextDTO,
    CommandContextDTO,
    CommandLogDTO,
    ConverterStateDTO,
    WorkspaceStateDTO,
)
from src.application.dto.command_entry import CommandEntryDTO, CommandLogEntryDTO
from src.presentation.repository.workspace_state import (
    ApplicationContextRepository,
    CommandLogRepository,
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


def test_command_log_roundtrip(tmp_path: Path):
    repository = CommandLogRepository(tmp_path)
    log = CommandLogDTO(
        entries=[
            CommandLogEntryDTO(input="1 + 1", success=True, message=None, result=2),
            CommandLogEntryDTO(
                input="1 / 0",
                success=False,
                message="Division by zero.",
                result=None,
            ),
        ]
    )

    saved_path = repository.save(log, Path("custom_log"))
    loaded = repository.load(saved_path)

    assert saved_path == repository.directory / "custom_log.json"
    assert loaded == log


def test_workspace_state_roundtrip_saves_context_and_log_together(tmp_path: Path):
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
        log=CommandLogDTO(
            entries=[
                CommandLogEntryDTO(
                    input="answer=42",
                    success=True,
                    message=None,
                    result=42,
                )
            ]
        ),
    )

    saved_path = repository.save(workspace, Path("full_workspace"))
    loaded = repository.load(saved_path)

    assert saved_path == repository.directory / "full_workspace.json"
    assert loaded == workspace
