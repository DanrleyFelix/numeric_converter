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


def test_heavy_binary_recovery_preview_does_not_materialize_rows(tmp_path: Path):
    """Recovery can identify the old tab before constructing row DTOs."""

    repository = BinaryWorkbenchContextRepository(tmp_path)
    target = repository.default_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({
            "tabs": [{
                "tab_id": "heavy",
                "kind": "assembly",
                "display_name": "heavy.asm",
                "rows": [{"instruction": "x" * (300 * 1024)}],
            }],
            "active_tab_id": "heavy",
        }),
        encoding="utf-8",
    )

    preview = repository.recovery_preview()

    assert preview is not None
    assert preview.active_tab_id == "heavy"
    assert [tab.display_name for tab in preview.tabs] == ["heavy.asm"]
    assert preview.tabs[0].rows == []


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


def test_binary_workbench_global_symbols_roundtrip_as_session_state(tmp_path: Path):
    repository = BinaryWorkbenchContextRepository(tmp_path)
    state = BinaryWorkbenchStateDTO(
        global_symbols={"shared_value": "0x20", "shared_address": "0x80010000"},
    )

    saved_path = repository.save(state)
    payload = json.loads(saved_path.read_text(encoding="utf-8"))
    loaded = repository.load(saved_path)

    assert payload["global_symbols"] == state.global_symbols
    assert loaded.global_symbols == state.global_symbols


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
    assert tab["symbols"] == {}
    assert "variables" not in tab
    assert "equates" not in tab
    assert tab["symbol_offsets"] == {}
    assert tab["custom_commands"] == {}
    assert tab["versions"] == []
    assert payload["commands_by_arch"] == {
        "PSX - Mips R3000A": {"save_regs": ["sw $a0, 0($sp)"]},
    }
    assert payload["encoding_tables"] == [
        {"name": "ansi", "values": {"0x41": "A"}},
    ]


def test_binary_workbench_legacy_symbol_fields_load_into_canonical_symbols():
    state = binary_workbench_state_from_payload(
        {
            "tabs": [
                {
                    "tab_id": "legacy",
                    "kind": "assembly",
                    "display_name": "legacy.asm",
                    "variables": {"old_var": "0x10"},
                    "equates": {"old_equate": "0x20"},
                    "versions": [
                        {
                            "name": "v1",
                            "variables": {"version_var": "0x30"},
                            "equates": {"version_equate": "0x40"},
                        }
                    ],
                }
            ]
        }
    )

    context = state.tabs[0]
    assert context.symbols == {
        "old_var": "0x10",
        "old_equate": "0x20",
    }
    assert context.variables == context.symbols
    assert context.equates == context.symbols
    assert context.versions[0].variables == {}
    assert context.versions[0].equates == {}
    assert context.versions[0].symbols_loaded is False

    payload = binary_workbench_state_to_payload(state)
    assert payload["tabs"][0]["symbols"] == context.symbols
    assert "variables" not in payload["tabs"][0]
    assert "equates" not in payload["tabs"][0]


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
        symbols={"variable1": "20", "equate1": "0x34"},
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
    assert loaded.symbols == {"variable1": "20", "equate1": "0x34"}
    assert loaded.variables == loaded.symbols
    assert loaded.equates == loaded.symbols
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


def test_binary_workbench_context_versions_roundtrip_symbols_and_natural_order():
    state = BinaryWorkbenchStateDTO(
        tabs=[
            BinaryWorkbenchTabContextDTO(
                tab_id="tab",
                kind="binary",
                display_name="versions.bin",
                symbols={"shared": "0x2"},
                versions=[
                    BinaryWorkbenchVersionDTO(
                        "v10",
                        variables={"var10": "0x10"},
                        equates={"eq10": "0x20"},
                        symbols_loaded=True,
                    ),
                    BinaryWorkbenchVersionDTO(
                        "v2",
                        variables={"var2": "0x2"},
                        equates={},
                        symbols_loaded=True,
                    ),
                    BinaryWorkbenchVersionDTO("v1"),
                ],
                active_version_name="v2",
            )
        ]
    )

    payload = binary_workbench_state_to_payload(state)
    loaded = binary_workbench_state_from_payload(payload)

    assert [version["name"] for version in payload["tabs"][0]["versions"]] == ["v1", "v2", "v10"]
    assert loaded.tabs[0].active_version_name == "v2"
    assert [version.name for version in loaded.tabs[0].versions] == ["v1", "v2", "v10"]
    assert loaded.tabs[0].symbols == {"shared": "0x2"}
    assert loaded.tabs[0].versions[1].variables == {}
    assert loaded.tabs[0].versions[1].symbols_loaded is False
    assert loaded.tabs[0].versions[0].symbols_loaded is False


def test_binary_workbench_workspace_versions_share_tab_symbols_and_keep_natural_order(tmp_path: Path):
    source = tmp_path / "versions.bin"
    source.write_bytes(bytes.fromhex("00 00 00 00"))
    repository = BinaryWorkbenchWorkspaceRepository(tmp_path)
    tab = BinaryWorkbenchTabContextDTO(
        tab_id="tab",
        kind="binary",
        display_name=source.name,
        source_path=str(source),
        symbols={"var2": "0x2", "eq2": "0x22"},
        versions=[
            BinaryWorkbenchVersionDTO(
                "v10",
                variables={"var10": "0x10"},
                equates={},
                symbols_loaded=True,
            ),
            BinaryWorkbenchVersionDTO(
                "v2",
                variables={"var2": "0x2"},
                equates={"eq2": "0x22"},
                symbols_loaded=True,
            ),
            BinaryWorkbenchVersionDTO(
                "v1",
                variables={},
                equates={},
                symbols_loaded=True,
            ),
        ],
        active_version_name="v2",
    )

    repository.save_tab_workspace(tab, repository.directory / "versions_manifest.json")
    version_path = repository.directory / "Versions" / "versions_manifest_versions.json"
    payload = json.loads(version_path.read_text(encoding="utf-8"))
    loaded = repository.load_tab_workspace(
        BinaryWorkbenchTabContextDTO(
            tab_id="fresh",
            kind="binary",
            display_name=source.name,
            source_path=str(source),
        ),
        repository.directory / "versions_manifest.json",
    )
    lazy_v10 = repository.load_version_from_context(loaded, "v10")

    assert payload["active_version"] == "v2"
    assert list(payload["versions"]) == ["v1", "v2", "v10"]
    assert "variables" not in payload["versions"]["v1"]
    assert "equates" not in payload["versions"]["v1"]
    assert loaded.active_version_name == "v2"
    assert loaded.symbols == {"var2": "0x2", "eq2": "0x22"}
    assert loaded.variables == loaded.symbols
    assert loaded.equates == loaded.symbols
    assert [version.name for version in loaded.versions] == ["v1", "v2", "v10"]
    assert lazy_v10 is not None
    assert lazy_v10.variables == {}
    assert lazy_v10.equates == {}


def test_binary_workbench_workspace_versions_use_shared_local_symbols(tmp_path: Path):
    source = tmp_path / "legacy.bin"
    source.write_bytes(bytes.fromhex("00 00 00 00"))
    repository = BinaryWorkbenchWorkspaceRepository(tmp_path)
    manifest = repository.directory / "legacy_manifest.json"
    saved = repository.save_tab_workspace(
        BinaryWorkbenchTabContextDTO(
            tab_id="tab",
            kind="binary",
            display_name=source.name,
            source_path=str(source),
            symbols={"legacy_var": "0x44", "legacy_eq": "0x55"},
            versions=[BinaryWorkbenchVersionDTO("v1")],
            active_version_name="v1",
        ),
        manifest,
    )
    version_path = Path(saved.module_paths[VERSIONS])
    payload = json.loads(version_path.read_text(encoding="utf-8"))
    payload["versions"]["v1"].pop("variables", None)
    payload["versions"]["v1"].pop("equates", None)
    version_path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = repository.load_tab_workspace(
        BinaryWorkbenchTabContextDTO(
            tab_id="fresh",
            kind="binary",
            display_name=source.name,
            source_path=str(source),
        ),
        manifest,
    )

    assert loaded.symbols == {"legacy_var": "0x44", "legacy_eq": "0x55"}
    assert loaded.variables == loaded.symbols
    assert loaded.equates == loaded.symbols
    assert loaded.versions[0].symbols_loaded is False


def test_binary_workbench_workspace_imports_external_module_into_fixed_directory(tmp_path: Path):
    repository = BinaryWorkbenchWorkspaceRepository(tmp_path)
    external_directory = tmp_path / "external"
    external_directory.mkdir()
    external = external_directory / "shared_symbols.json"
    external.write_text('{"name":"shared","variables":{"value":"0x10"},"equates":{}}', encoding="utf-8")

    imported = repository.import_environment_file(SYMBOLS, external)

    assert imported == repository.directory / "Symbols" / external.name
    assert imported.read_text(encoding="utf-8") == external.read_text(encoding="utf-8")


def test_binary_workbench_workspace_save_rehomes_external_module_paths(tmp_path: Path):
    repository = BinaryWorkbenchWorkspaceRepository(tmp_path)
    external_directory = tmp_path / "external"
    external_directory.mkdir()
    external = external_directory / "custom_symbols.json"
    external.write_text('{"untouched":true}', encoding="utf-8")
    tab = BinaryWorkbenchTabContextDTO(
        tab_id="tab",
        kind="scratch",
        display_name="scratch",
        symbols={"value": "0x20"},
        module_paths={SYMBOLS: str(external)},
        module_directories={SYMBOLS: str(external_directory)},
    )

    saved = repository.save_tab_workspace(tab)

    expected = repository.directory / "Symbols" / external.name
    assert saved.module_paths[SYMBOLS] == str(expected)
    assert saved.module_directories[SYMBOLS] == str(repository.directory / "Symbols")
    assert json.loads(expected.read_text(encoding="utf-8"))["symbols"] == {"value": "0x20"}
    assert json.loads(external.read_text(encoding="utf-8")) == {"untouched": True}
