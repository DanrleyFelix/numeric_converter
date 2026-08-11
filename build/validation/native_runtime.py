"""Reject foreign runtimes that can destabilize packaged native libraries."""

from __future__ import annotations

import hashlib
import os
import platform
import struct
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Iterable

WINDOWS_X64_MACHINE = 0x8664
WINDOWS_PE64_MAGIC = 0x20B
WINDOWS_GUARD_CF_FLAG = 0x4000
FORBIDDEN_WINDOWS_RUNTIME = "ucrtbase.dll"
FORBIDDEN_API_SET_PREFIX = "api-ms-win-"


def validate_build_environment(
    target_os: str,
    requirements_path: Path,
    native_entries: Iterable[tuple[str, str]],
) -> None:
    """Validate pinned tooling and x64 native inputs before packaging."""

    expected = _required_pyinstaller_version(requirements_path)
    installed = version("pyinstaller")
    if installed != expected:
        raise RuntimeError(
            f"PyInstaller {expected} is required; installed version is {installed}."
        )
    if target_os != "windows":
        return
    if struct.calcsize("P") != 8 or platform.machine().casefold() not in {
        "amd64",
        "x86_64",
        "x64",
    }:
        raise RuntimeError("Windows releases require an x86-64 Python runtime.")
    for source, _target in native_entries:
        path = Path(source)
        if path.suffix.casefold() == ".dll" and _pe_machine(path) != WINDOWS_X64_MACHINE:
            raise RuntimeError(f"Native library is not x86-64: {path}")


def sanitized_build_environment(project_root: Path) -> dict[str, str]:
    """Return a PyInstaller environment without JDK or foreign PATH entries."""

    environment = dict(os.environ)
    system_root = Path(environment.get("SystemRoot", "C:/Windows"))
    candidates = (
        Path(sys.executable).resolve().parent,
        Path(sys.prefix).resolve(),
        Path(sys.prefix).resolve() / "Scripts",
        Path(sys.prefix).resolve() / "DLLs",
        project_root.resolve(),
        system_root,
        system_root / "System32",
        system_root / "System32" / "Wbem",
    )
    environment["PATH"] = os.pathsep.join(
        str(path) for path in candidates if path.exists()
    )
    environment["PYTHONNOUSERSITE"] = "1"
    for name in ("JAVA_HOME", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS", "CLASSPATH"):
        environment.pop(name, None)
    return environment


def validate_analysis_binary_origins(entries: Iterable[tuple], project_root: Path) -> None:
    """Reject Analysis binaries sourced outside Python, project, or Windows."""

    system_root = Path(os.environ.get("SystemRoot", "C:/Windows")).resolve()
    allowed = {
        project_root.resolve(),
        Path(sys.prefix).resolve(),
        Path(sys.base_prefix).resolve(),
        system_root,
    }
    for entry in entries:
        if len(entry) < 2:
            continue
        source = Path(str(entry[1])).resolve()
        if source.suffix.casefold() not in {".dll", ".pyd"}:
            continue
        if not any(source == root or source.is_relative_to(root) for root in allowed):
            raise RuntimeError(f"Foreign native library rejected: {source}")


def disable_incompatible_control_flow_guard(executable: Path) -> None:
    """Disable bootloader CFG, which rejects Unicorn's generated JIT targets."""

    with executable.open("r+b") as stream:
        optional_header = _pe_optional_header_offset(stream, executable)
        stream.seek(optional_header)
        magic = struct.unpack("<H", stream.read(2))[0]
        if magic != WINDOWS_PE64_MAGIC:
            raise RuntimeError(f"Expected one PE32+ executable: {executable}")
        dll_characteristics_offset = optional_header + 0x46
        stream.seek(dll_characteristics_offset)
        characteristics = struct.unpack("<H", stream.read(2))[0]
        stream.seek(dll_characteristics_offset)
        stream.write(struct.pack("<H", characteristics & ~WINDOWS_GUARD_CF_FLAG))


def validate_windows_artifact(
    artifact_root: Path,
    source_entries: Iterable[tuple[str, str]],
) -> None:
    """Validate native layout, integrity, architecture, and runtime isolation."""

    files = tuple(path for path in artifact_root.rglob("*") if path.is_file())
    forbidden = [path for path in files if _forbidden_runtime_name(path.name)]
    if forbidden:
        raise RuntimeError(f"Foreign UCRT/API-set library packaged: {forbidden[0]}")
    executable = artifact_root / "NumericWorkBench.exe"
    if _pe_machine(executable) != WINDOWS_X64_MACHINE:
        raise RuntimeError("NumericWorkBench.exe is not an x86-64 PE executable.")
    if _pe_dll_characteristics(executable) & WINDOWS_GUARD_CF_FLAG:
        raise RuntimeError(
            "NumericWorkBench.exe still enables CFG, which is incompatible with "
            "the packaged Unicorn JIT runtime."
        )
    unicorns = [path for path in files if path.name.casefold() == "unicorn.dll"]
    keystones = [path for path in files if path.name.casefold() == "keystone.dll"]
    if len(unicorns) != 1 or "unicorn/lib" not in unicorns[0].as_posix().casefold():
        raise RuntimeError("Build must contain one unicorn/lib/unicorn.dll.")
    if len(keystones) != 1:
        raise RuntimeError("Build must contain one Keystone native library.")
    sources = {Path(source).name.casefold(): Path(source) for source, _ in source_entries}
    for packaged in (*unicorns, *keystones):
        if _pe_machine(packaged) != WINDOWS_X64_MACHINE:
            raise RuntimeError(f"Packaged native library is not x86-64: {packaged}")
        source = sources.get(packaged.name.casefold())
        if source is None or _sha256(source) != _sha256(packaged):
            raise RuntimeError(f"Packaged native library failed integrity check: {packaged}")


def _required_pyinstaller_version(requirements_path: Path) -> str:
    """Read the exact PyInstaller version required by release configuration."""

    for line in requirements_path.read_text(encoding="utf-8").splitlines():
        name, separator, pinned = line.partition("==")
        if separator and name.strip().casefold() == "pyinstaller":
            return pinned.strip()
    raise RuntimeError("requirements-build.txt must pin PyInstaller with ==.")


def _forbidden_runtime_name(name: str) -> bool:
    """Return whether a bundled name belongs to the Windows-provided UCRT."""

    normalized = name.casefold()
    return normalized == FORBIDDEN_WINDOWS_RUNTIME or (
        normalized.startswith(FORBIDDEN_API_SET_PREFIX) and normalized.endswith(".dll")
    )


def _pe_machine(path: Path) -> int:
    """Read the COFF machine identifier from one PE image."""

    with path.open("rb") as stream:
        offset = _pe_header_offset(stream, path)
        stream.seek(offset + 4)
        return struct.unpack("<H", stream.read(2))[0]


def _pe_dll_characteristics(path: Path) -> int:
    """Read the DLL characteristics flags from one PE32+ executable."""

    with path.open("rb") as stream:
        optional_header = _pe_optional_header_offset(stream, path)
        stream.seek(optional_header)
        if struct.unpack("<H", stream.read(2))[0] != WINDOWS_PE64_MAGIC:
            raise RuntimeError(f"Expected one PE32+ executable: {path}")
        stream.seek(optional_header + 0x46)
        return struct.unpack("<H", stream.read(2))[0]


def _pe_optional_header_offset(stream, path: Path) -> int:
    """Locate the optional header of one validated PE image."""

    return _pe_header_offset(stream, path) + 4 + 20


def _pe_header_offset(stream, path: Path) -> int:
    """Locate and validate the COFF header of one PE image."""

    stream.seek(0)
    if stream.read(2) != b"MZ":
        raise RuntimeError(f"Not a PE image: {path}")
    stream.seek(0x3C)
    offset = struct.unpack("<I", stream.read(4))[0]
    stream.seek(offset)
    if stream.read(4) != b"PE\0\0":
        raise RuntimeError(f"Invalid PE signature: {path}")
    return offset


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest of one native binary."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
