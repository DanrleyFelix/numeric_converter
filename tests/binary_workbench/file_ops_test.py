from pathlib import Path

import pytest

from src.core.binary_workbench.file_ops import save_versioned_binary
from src.modules.dtos import BinaryWorkbenchRowDTO


def test_save_versioned_binary_refuses_to_overwrite_source_file(tmp_path: Path):
    source = tmp_path / "source.bin"
    source.write_bytes(bytes.fromhex("00 FF FF FF 01 02 03 04"))
    rows = [
        BinaryWorkbenchRowDTO(
            offsets={"File": "0x00000004"},
            bytes_text="AA BB CC DD",
        )
    ]

    with pytest.raises(ValueError):
        save_versioned_binary(source, source, rows)

    assert source.read_bytes() == bytes.fromhex("00 FF FF FF 01 02 03 04")