from pathlib import Path

from src.modules.dtos import (
    ApplicationContextDTO,
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchLbaFilesystemDTO,
    BinaryWorkbenchMemoryRegionDTO,
    BinaryWorkbenchRowDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchSymbolsDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchVersionDTO,
    CommandContextDTO,
    ConverterStateDTO,
    WorkspaceStateDTO,
)
from src.modules.dtos import CommandEntryDTO
from src.presentation.repository.workspace_state import (
    ApplicationContextRepository,
    WorkspaceStateRepository,
)
from src.presentation.repository.binary_workbench_workspace import (
    BinaryWorkbenchWorkspaceRepository,
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
            recent_files=["C:/tmp/sample.bin"],
            directories={"open_binary": "C:/tmp", "open_assembly": "", "save_file": "C:/tmp", "save_assembly": ""},
            lba_filesystems=[
                BinaryWorkbenchLbaFilesystemDTO(
                    name="disc-map",
                    file_identifiers=["name:sample.bin"],
                    sector_size=2048,
                    internal_files=[BinaryWorkbenchInternalFileDTO("slus", 24)],
                )
            ],
            symbols=[
                BinaryWorkbenchSymbolsDTO(
                    name="shared-symbols",
                    file_identifiers=["name:sample.bin"],
                    variables={"variable1": "20"},
                    equates={"equate1": "0x34"},
                    labels={"label1": "0x00000000"},
                )
            ],
        ),
        key_panel_visible=False,
    )

    saved_path = repository.save(context, Path("session_one"))
    loaded = repository.load(saved_path)
    expected = ApplicationContextDTO(
        **{
            **context.__dict__,
            "binary_workbench": BinaryWorkbenchStateDTO(
                tabs=[
                    BinaryWorkbenchTabContextDTO(
                        **{
                            **context.binary_workbench.tabs[0].__dict__,
                            "rows": [],
                            "original_rows": [],
                            "reference_offsets": ["File"],
                            "reference_offset_bases": {"File": "0x00000000"},
                        }
                    )
                ],
                active_tab_id="binary-1",
                recent_files=["C:/tmp/sample.bin"],
                directories={
                    **BinaryWorkbenchStateDTO().directories,
                    **context.binary_workbench.directories,
                },
                lba_filesystems=list(context.binary_workbench.lba_filesystems),
                symbols=list(context.binary_workbench.symbols),
            ),
        }
    )

    assert saved_path == repository.directory / "session_one.json"
    assert loaded == expected


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
                        instruction_overlays={"0x00000000": "LOOP: ADDIU $S1, $ZERO, _VARIABLE1"},
                    )
                ],
                active_tab_id="scratch-1",
                recent_files=["C:/tmp/scratch.asm"],
                directories={"open_binary": "", "open_assembly": "C:/tmp", "save_file": "", "save_assembly": ""},
            ),
            key_panel_visible=True,
        ),
    )

    saved_path = repository.save(workspace, Path("full_workspace"))
    loaded = repository.load(saved_path)
    expected = WorkspaceStateDTO(
        context=ApplicationContextDTO(
            **{
                **workspace.context.__dict__,
                "binary_workbench": BinaryWorkbenchStateDTO(
                    tabs=[
                        BinaryWorkbenchTabContextDTO(
                            **{
                                **workspace.context.binary_workbench.tabs[0].__dict__,
                                "reference_offsets": ["File"],
                                "reference_offset_bases": {"File": "0x00000000"},
                            }
                        )
                    ],
                    active_tab_id="scratch-1",
                    recent_files=["C:/tmp/scratch.asm"],
                    directories={
                        **BinaryWorkbenchStateDTO().directories,
                        **workspace.context.binary_workbench.directories,
                    },
                ),
            }
        )
    )

    assert saved_path == repository.directory / "full_workspace.json"
    assert loaded == expected


def test_binary_workbench_workspace_manifest_roundtrip_modules(tmp_path: Path):
    source = tmp_path / "disc.bin"
    source.write_bytes(bytes.fromhex("00 00 00 00"))
    repository = BinaryWorkbenchWorkspaceRepository(tmp_path)
    tab = BinaryWorkbenchTabContextDTO(
        tab_id="tab",
        kind="binary",
        display_name=source.name,
        source_path=str(source),
        variables={"variable1": "20"},
        equates={"equate1": "0x34"},
        internal_files=[BinaryWorkbenchInternalFileDTO("slus", 24)],
        memory_regions=[BinaryWorkbenchMemoryRegionDTO("SLUS code", 0x1C2400, 0x1C24FF)],
        versions=[
            BinaryWorkbenchVersionDTO(
                "v1",
                instruction_overlays={
                    "0x00000000": "Label_1: ADDIU $S1, $S1, _variable1"
                },
            )
        ],
        active_version_name="v1",
    )

    saved = repository.save_tab_workspace(tab, repository.directory / "ygo_fm_wicked.json")
    manifest = repository.directory / "ygo_fm_wicked.json"
    version_file = repository.directory / "Versions" / "ygo_fm_wicked_v1.json"
    loaded = repository.load_tab_workspace(
        BinaryWorkbenchTabContextDTO(
            tab_id="fresh",
            kind="binary",
            display_name=source.name,
            source_path=str(source),
        ),
        manifest,
    )

    assert saved.workspace_path == str(manifest)
    assert manifest.exists()
    assert version_file.exists()
    assert '"offset": 0' in version_file.read_text(encoding="utf-8")
    assert loaded.variables == {"variable1": "20"}
    assert loaded.equates == {"equate1": "0x34"}
    assert loaded.internal_files == [BinaryWorkbenchInternalFileDTO("slus", 24)]
    assert loaded.memory_regions == [
        BinaryWorkbenchMemoryRegionDTO("SLUS code", 0x1C2400, 0x1C24FF)
    ]
    assert loaded.active_version_name == "v1"
    assert loaded.instruction_overlays["0x00000000"].startswith("Label_1:")
    assert loaded.byte_overlays["0x00000000"] != "00 00 00 00"


def test_binary_workbench_workspace_matches_exact_directory_and_filename(tmp_path: Path):
    first = tmp_path / "one" / "disc.bin"
    second = tmp_path / "two" / "disc.bin"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_bytes(b"\x00\x00\x00\x00")
    second.write_bytes(b"\x00\x00\x00\x00")
    repository = BinaryWorkbenchWorkspaceRepository(tmp_path)

    repository.save_tab_workspace(
        BinaryWorkbenchTabContextDTO(
            tab_id="tab",
            kind="binary",
            display_name=first.name,
            source_path=str(first),
        ),
        repository.directory / "disc_workspace.json",
    )

    assert repository.find_for_source(first) == repository.directory / "disc_workspace.json"
    assert repository.find_for_source(second) is None
