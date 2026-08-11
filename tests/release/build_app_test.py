import subprocess
import struct
from pathlib import Path

import pytest # type: ignore

from build.build_app import (
    _run_packaged_debugger_smoke,
    _validate_artifact,
)
from build.validation.native_runtime import (
    WINDOWS_GUARD_CF_FLAG,
    disable_incompatible_control_flow_guard,
    sanitized_build_environment,
    validate_analysis_binary_origins,
    validate_build_environment,
    validate_windows_artifact,
)


def _write_test_pe(path: Path, dll_characteristics: int) -> None:
    """Write the minimal PE64 headers needed by native build guards."""

    image = bytearray(512)
    image[0:2] = b"MZ"
    struct.pack_into("<I", image, 0x3C, 0x80)
    image[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", image, 0x84, 0x8664)
    optional = 0x80 + 4 + 20
    struct.pack_into("<H", image, optional, 0x20B)
    struct.pack_into("<H", image, optional + 0x46, dll_characteristics)
    path.write_bytes(image)


def test_validate_artifact_accepts_packaged_executable(tmp_path: Path):
    executable = tmp_path / "NumericWorkBench.exe"
    executable.write_text("", encoding="utf-8")

    _validate_artifact(tmp_path)


def test_validate_artifact_rejects_missing_output(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="no executable/app bundle"):
        _validate_artifact(tmp_path)


def test_build_environment_rejects_wrong_pyinstaller_version(
    tmp_path: Path,
    monkeypatch,
):
    """Fail before packaging when the release tool differs from its pin."""

    requirements = tmp_path / "requirements-build.txt"
    requirements.write_text("pyinstaller==6.16.0\n", encoding="utf-8")
    monkeypatch.setattr(
        "build.validation.native_runtime.version",
        lambda _name: "6.11.0",
    )

    with pytest.raises(RuntimeError, match="PyInstaller 6.16.0 is required"):
        validate_build_environment("linux", requirements, ())


def test_sanitized_environment_excludes_java_runtime_paths(
    tmp_path: Path,
    monkeypatch,
):
    """Remove JDK search paths and Java variables from PyInstaller startup."""

    monkeypatch.setenv("PATH", "C:/Adoptium/jdk/bin")
    monkeypatch.setenv("JAVA_HOME", "C:/Adoptium/jdk")

    environment = sanitized_build_environment(tmp_path)

    assert "adoptium" not in environment["PATH"].casefold()
    assert "JAVA_HOME" not in environment


def test_analysis_rejects_native_library_from_jdk(tmp_path: Path):
    """Reject a foreign native origin even before bundle-name filtering."""

    entries = [("ucrtbase.dll", "C:/Program Files/Eclipse Adoptium/jdk/bin/ucrtbase.dll", "BINARY")]

    with pytest.raises(RuntimeError, match="Foreign native library rejected"):
        validate_analysis_binary_origins(entries, tmp_path)


def test_windows_artifact_rejects_foreign_ucrt(tmp_path: Path):
    """Reject an artifact if a Windows-owned runtime DLL was collected."""

    (tmp_path / "ucrtbase.dll").write_bytes(b"foreign")

    with pytest.raises(RuntimeError, match="Foreign UCRT/API-set"):
        validate_windows_artifact(tmp_path, ())


def test_build_disables_pyinstaller_cfg_for_unicorn_jit(tmp_path: Path):
    """Remove only GUARD_CF while preserving all unrelated PE flags."""

    executable = tmp_path / "NumericWorkBench.exe"
    original = 0x8160 | WINDOWS_GUARD_CF_FLAG
    _write_test_pe(executable, original)

    disable_incompatible_control_flow_guard(executable)

    image = executable.read_bytes()
    optional = 0x80 + 4 + 20
    updated = struct.unpack_from("<H", image, optional + 0x46)[0]
    assert updated == original & ~WINDOWS_GUARD_CF_FLAG


def test_packaged_smoke_rejects_native_process_failure(tmp_path: Path, monkeypatch):
    """Treat a fail-fast process exit as a failed release build."""

    monkeypatch.setattr(
        "build.build_app.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0xC0000409, "", ""),
    )

    with pytest.raises(RuntimeError, match="smoke test failed"):
        _run_packaged_debugger_smoke(tmp_path)
