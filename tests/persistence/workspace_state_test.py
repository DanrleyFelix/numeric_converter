import json
from pathlib import Path

from src.modules.dtos import (
    ApplicationContextDTO,
    BinaryWorkbenchEncodingTableDTO,
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchRowDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchVersionDTO,
    CommandContextDTO,
    CommandEntryDTO,
    ConverterStateDTO,
    ProgramContextDTO,
    WindowSizeDTO,
    WorkspaceStateDTO,
)
from src.presentation.repository.binary_workbench_workspace import (
    BinaryWorkbenchWorkspaceRepository,
)
from src.presentation.repository.binary_workbench_workspace.constants import (
    OFFSET_REGIONS,
    SYMBOLS,
    VERSIONS,
)
from src.presentation.repository.binary_workbench_payload import (
    binary_workbench_state_from_payload,
    binary_workbench_state_to_payload,
)
from src.presentation.repository.workspace_state import (
    ApplicationContextRepository,
    BinaryWorkbenchContextRepository,
    ProgramContextRepository,
    WorkspaceStateRepository,
)


def test_application_context_roundtrip_uses_numeric_workbench_context_path(tmp_path: Path):
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
        window_sizes={"main_window": WindowSizeDTO(width=900, height=600)},
    )

    saved_path = repository.save(context, Path("session_one"))
    loaded = repository.load(saved_path)

    assert saved_path == repository.directory / "session_one.json"
    assert loaded == context


def test_binary_workbench_context_roundtrip_excludes_program_and_preferences(tmp_path: Path):
    repository = BinaryWorkbenchContextRepository(tmp_path)
    state = BinaryWorkbenchStateDTO(
        tabs=[
            BinaryWorkbenchTabContextDTO(
                tab_id="binary-1",
                kind="binary",
                display_name="sample.bin",
                source_path="C:/tmp/sample.bin",
                rows=[
                    BinaryWorkbenchRowDTO(
                        offsets={"File": "0x00000004", "RAM": "0x80010004"},
                        instruction="JAL 0x1D9200",
                        bytes_text="80 64 07 0C",
                    )
                ],
            )
        ],
        active_tab_id="binary-1",
        window_size=WindowSizeDTO(width=1200, height=720),
    )

    saved_path = repository.save(state)
    payload = json.loads(saved_path.read_text(encoding="utf-8"))
    loaded = repository.load(saved_path)

    assert saved_path == repository.default_path()
    assert "recent_files" not in payload
    assert "navigation_mode" not in payload["tabs"][0]
    assert "block_size" not in payload["tabs"][0]
    assert "cache_max_blocks" not in payload["tabs"][0]
    assert "group_bytes" not in payload["tabs"][0]["view_preferences"]
    assert payload["tabs"][0]["rows"] == []
    assert payload["tabs"][0]["original_rows"] == []
    assert payload["tabs"][0]["byte_overlays"] == {}
    assert payload["tabs"][0]["instruction_overlays"] == {}
    assert loaded == BinaryWorkbenchStateDTO(
        tabs=[
            BinaryWorkbenchTabContextDTO(
                **{
                    **state.tabs[0].__dict__,
                    "rows": [],
                    "original_rows": [],
                    "reference_offsets": ["File"],
                    "reference_offset_bases": {"File": "0x00000000"},
                }
            )
        ],
        active_tab_id="binary-1",
        window_size=WindowSizeDTO(width=1200, height=720),
    )


def test_binary_workbench_context_discards_legacy_blank_instruction_overlay():
    state = binary_workbench_state_from_payload(
        {
            "tabs": [
                {
                    "tab_id": "binary-1",
                    "kind": "binary",
                    "display_name": "sample.bin",
                    "byte_overlays": {"0x00000000": "00 00 00 00"},
                    "instruction_overlays": {"0x00000000": ""},
                    "version_dirty": True,
                }
            ]
        }
    )

    assert state.tabs[0].byte_overlays == {}
    assert state.tabs[0].instruction_overlays == {}
    assert state.tabs[0].version_dirty is False


def test_binary_workbench_context_discards_legacy_nop_overlay_from_empty_version(tmp_path: Path):
    source = tmp_path / "source.bin"
    source.write_bytes(bytes.fromhex("00 FF FF FF"))
    state = binary_workbench_state_from_payload(
        {
            "tabs": [
                {
                    "tab_id": "binary-1",
                    "kind": "binary",
                    "display_name": source.name,
                    "source_path": str(source),
                    "active_version_name": "v1 test",
                    "versions": [{"name": "v1 test", "rows": [], "instructions": []}],
                    "byte_overlays": {"0x00000000": "00 00 00 00"},
                    "instruction_overlays": {"0x00000000": "NOP"},
                    "version_dirty": True,
                }
            ]
        }
    )

    assert state.tabs[0].byte_overlays == {}
    assert state.tabs[0].instruction_overlays == {}
    assert state.tabs[0].version_dirty is False


def test_binary_workbench_context_payload_excludes_binary_line_edits(tmp_path: Path):
    source = tmp_path / "source.bin"
    source.write_bytes(bytes.fromhex("00 00 00 00 01 02 03 04"))
    payload = binary_workbench_state_to_payload(
        BinaryWorkbenchStateDTO(
            tabs=[
                BinaryWorkbenchTabContextDTO(
                    tab_id="binary-1",
                    kind="binary",
                    display_name=source.name,
                    source_path=str(source),
                    byte_overlays={"0x00000004": "00 00 00 00"},
                    instruction_overlays={
                        "0x00000000": "NOP",
                        "0x00000004": "NOP",
                    },
                    version_dirty=True,
                )
            ]
        )
    )

    assert payload["tabs"][0]["byte_overlays"] == {}
    assert payload["tabs"][0]["instruction_overlays"] == {}
    assert payload["tabs"][0]["version_dirty"] is True


def test_binary_workbench_context_payload_omits_module_backed_heavy_data():
    payload = binary_workbench_state_to_payload(
        BinaryWorkbenchStateDTO(
            tabs=[
                BinaryWorkbenchTabContextDTO(
                    tab_id="binary-1",
                    kind="binary",
                    display_name="sample.bin",
                    variables={"hp": "0x20"},
                    equates={"max": "0x64"},
                    labels={"loop": "0x00000010"},
                    symbol_offsets={"loop": ["0x00000010"]},
                    versions=[BinaryWorkbenchVersionDTO("v1")],
                    active_version_name="v1",
                    workspace_path="C:/workspaces/sample.json",
                    module_paths={
                        SYMBOLS: "Symbols/sample_symbols.json",
                        VERSIONS: "Versions/sample_versions.json",
                        OFFSET_REGIONS: "Offset Regions/sample_offset_regions.json",
                    },
                )
            ],
            commands_by_arch={
                "PSX - Mips R3000A": {"save_regs": ["sw $a0, 0($sp)"]},
            },
            encoding_tables=[
                BinaryWorkbenchEncodingTableDTO("ansi", {0x41: "A"}),
            ],
        )
    )

    tab = payload["tabs"][0]
    assert tab["labels"] == {}
    assert tab["variables"] == {}
    assert tab["equates"] == {}
    assert tab["symbol_offsets"] == {}
    assert tab["custom_commands"] == {}
    assert tab["versions"] == []
    assert payload["commands_by_arch"] == {
        "PSX - Mips R3000A": {"save_regs": ["sw $a0, 0($sp)"]},
    }
    assert payload["encoding_tables"] == [
        {"name": "ansi", "values": {"0x41": "A"}},
    ]


def test_program_context_roundtrip_tracks_recent_and_last_binary_workspace(tmp_path: Path):
    repository = ProgramContextRepository(tmp_path)
    context = ProgramContextDTO(
        recent_files=["C:/tmp/sample.bin"],
        last_binary_workspaces={"path:c:/tmp/sample.bin": "C:/workspaces/sample.json"},
    )

    repository.save(context)

    assert repository.load() == context


def test_workspace_state_roundtrip_saves_numeric_context(tmp_path: Path):
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
        ),
    )

    saved_path = repository.save(workspace, Path("full_workspace"))
    loaded = repository.load(saved_path)

    assert saved_path == repository.directory / "full_workspace.json"
    assert loaded == workspace


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
        versions=[
            BinaryWorkbenchVersionDTO(
                "v1",
                instructions_by_line={
                    0: "Label_1: ADDIU $S1, $S1, _variable1"
                },
            )
        ],
        active_version_name="v1",
        version_dirty=True,
    )

    saved = repository.save_tab_workspace(tab, repository.directory / "ygo_fm_wicked.json")
    manifest = repository.directory / "ygo_fm_wicked.json"
    version_file = repository.directory / "Versions" / "ygo_fm_wicked_versions.json"
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
    assert saved.version_dirty is False
    assert manifest.exists()
    assert version_file.exists()
    assert '"0"' in version_file.read_text(encoding="utf-8")
    assert loaded.variables == {"variable1": "20"}
    assert loaded.equates == {"equate1": "0x34"}
    assert loaded.internal_files == [BinaryWorkbenchInternalFileDTO("slus", 24)]
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


def test_binary_workbench_workspace_uses_preferred_manifest_when_multiple_match(tmp_path: Path):
    source = tmp_path / "disc.bin"
    source.write_bytes(b"\x00\x00\x00\x00")
    repository = BinaryWorkbenchWorkspaceRepository(tmp_path)

    first = repository.save_tab_workspace(
        BinaryWorkbenchTabContextDTO(
            tab_id="one",
            kind="binary",
            display_name=source.name,
            source_path=str(source),
        ),
        repository.directory / "first.json",
    )
    second = repository.save_tab_workspace(
        BinaryWorkbenchTabContextDTO(
            tab_id="two",
            kind="binary",
            display_name=source.name,
            source_path=str(source),
        ),
        repository.directory / "second.json",
    )

    assert repository.find_for_source(source) is None
    assert repository.find_for_source(source, Path(first.workspace_path or "")) == Path(first.workspace_path or "")
    assert repository.find_for_source(source, Path(second.workspace_path or "")) == Path(second.workspace_path or "")
