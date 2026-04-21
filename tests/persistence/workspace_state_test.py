from pathlib import Path

from src.application.dto.application_state import (
    ApplicationContextDTO,
    CommandContextDTO,
    CommandLogDTO,
    ConverterStateDTO,
)
from src.application.dto.command_entry import CommandEntryDTO, CommandLogEntryDTO
from src.presentation.repository.workspace_state import (
    ApplicationContextRepository,
    CommandLogRepository,
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
