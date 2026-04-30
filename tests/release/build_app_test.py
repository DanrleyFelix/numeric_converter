from pathlib import Path

import pytest # type: ignore

from build.build_app import _validate_artifact


def test_validate_artifact_accepts_packaged_executable(tmp_path: Path):
    executable = tmp_path / "NumericWorkBench.exe"
    executable.write_text("", encoding="utf-8")

    _validate_artifact(tmp_path)


def test_validate_artifact_rejects_missing_output(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="no executable/app bundle"):
        _validate_artifact(tmp_path)
