from pathlib import Path

from src.modules.dtos import (
    ApplicationContextDTO,
    BinaryWorkbenchRowDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
    CommandContextDTO,
    ConverterStateDTO,
    WorkspaceStateDTO,
)
from src.modules.dtos import CommandEntryDTO
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
        binary_workbench=BinaryWorkbenchStateDTO(
            tabs=[
                BinaryWorkbenchTabContextDTO(
                    tab_id="binary-1",
                    kind="binary",
                    display_name="sample.bin",
                    source_path="C:/tmp/sample.bin",
                    rows=[
                        BinaryWorkbenchRowDTO(
                            offsets={"File": "0x00000000", "RAM": "0x80010000"},
                            instruction="word 0x00000000",
                            bytes_text="00 00 00 00",
                        )
                    ],
                )
            ],
            active_tab_id="binary-1",
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
            binary_workbench=BinaryWorkbenchStateDTO(
                tabs=[
                    BinaryWorkbenchTabContextDTO(
                        tab_id="scratch-1",
                        kind="scratch",
                        display_name="Scratch 1",
                        rows=[
                            BinaryWorkbenchRowDTO(
                                offsets={"File": "0x00000000", "RAM": "0x80010000"},
                                instruction="word 0x246301F4",
                                bytes_text="F4 01 63 24",
                            )
                        ],
                    )
                ],
                active_tab_id="scratch-1",
            ),
            key_panel_visible=True,
        ),
    )

    saved_path = repository.save(workspace, Path("full_workspace"))
    loaded = repository.load(saved_path)

    assert saved_path == repository.directory / "full_workspace.json"
    assert loaded == workspace
