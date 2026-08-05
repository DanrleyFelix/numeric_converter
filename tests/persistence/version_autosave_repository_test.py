from pathlib import Path

from src.modules.dtos import (
    BinaryWorkbenchRowDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchVersionDTO,
)
from src.modules.utils import read_json, write_json
from src.presentation.repository.binary_workbench_workspace.constants import (
    SYMBOLS,
    VERSIONS,
)
from src.presentation.repository.binary_workbench_workspace import (
    BinaryWorkbenchWorkspaceRepository,
)
from src.presentation.repository.binary_workbench_workspace.payloads import (
    versions_from_payload,
    versions_payload,
)


def test_active_version_autosave_writes_no_other_workspace_module(tmp_path: Path):
    repository = BinaryWorkbenchWorkspaceRepository(tmp_path)
    versions_path = tmp_path / "versions.json"
    symbols_path = tmp_path / "symbols.json"
    manifest_path = tmp_path / "workspace.json"
    previous = BinaryWorkbenchVersionDTO(
        "active",
        [BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "00 00 00 00")],
    )
    untouched = BinaryWorkbenchVersionDTO(
        "other",
        [BinaryWorkbenchRowDTO({"File": "0x00000000"}, "jr $ra", "08 00 E0 03")],
    )
    write_json(versions_path, versions_payload([previous, untouched], "active"))
    write_json(symbols_path, {"symbols": {"keep": "0x10"}})
    symbols_before = symbols_path.read_bytes()
    updated = BinaryWorkbenchVersionDTO(
        "active",
        [BinaryWorkbenchRowDTO({"File": "0x00000000"}, "jr $ra", "08 00 E0 03")],
    )
    context = BinaryWorkbenchTabContextDTO(
        "tab",
        "assembly",
        "source.asm",
        workspace_path=str(manifest_path),
        module_paths={VERSIONS: str(versions_path), SYMBOLS: str(symbols_path)},
        versions=[updated],
        active_version_name="active",
    )

    paths = repository.save_active_version(context)

    stored_path = Path(paths[VERSIONS])
    stored = {item.name: item for item in versions_from_payload(read_json(stored_path))}
    assert stored["active"].rows[0].instruction.lower() == "jr $ra"
    assert stored["other"].rows == untouched.rows
    assert symbols_path.read_bytes() == symbols_before
    assert not manifest_path.exists()
    assert stored_path.name == versions_path.name
