from __future__ import annotations

import platform
import sys
from pathlib import Path

APP_NAME = "Numeric WorkBench"
APP_VERSION = "2.0"
EXECUTABLE_NAME = "NumericWorkBench"
SUPPORTED_OSES = ("windows", "linux", "macos")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT = PROJECT_ROOT / "dist"
PYINSTALLER_WORK_ROOT = PROJECT_ROOT / "build" / ".pyinstaller"
GENERATED_ROOT = PROJECT_ROOT / "build" / "generated"
WINDOWS_ICON_PATH = GENERATED_ROOT / "app.ico"
SPEC_PATH = PROJECT_ROOT / "build" / "pyinstaller" / "numeric_workbench.spec"

_PLATFORM_TO_OS = {
    "win32": "windows",
    "linux": "linux",
    "darwin": "macos",
}
_ARCH_ALIASES = {
    "amd64": "x86_64",
    "x64": "x86_64",
    "x86_64": "x86_64",
    "arm64": "arm64",
    "aarch64": "arm64",
}


def current_os_name() -> str:
    return _PLATFORM_TO_OS.get(sys.platform, sys.platform)


def normalized_architecture() -> str:
    machine = platform.machine().lower()
    return _ARCH_ALIASES.get(machine, machine or "unknown")


def artifact_directory_name(target_os: str) -> str:
    return (
        f"numeric-workbench-v{APP_VERSION}-{target_os}-"
        f"{normalized_architecture()}"
    )


def validate_target_os(target_os: str) -> str:
    normalized = target_os.lower().strip()
    if normalized not in SUPPORTED_OSES:
        supported = ", ".join(SUPPORTED_OSES)
        raise ValueError(
            f"Unsupported OS '{target_os}'. Use one of: {supported}."
        )
    native_os = current_os_name()
    if normalized != native_os:
        raise ValueError(
            "Portable builds must be created natively. "
            f"Current host is '{native_os}', requested '{normalized}'."
        )
    return normalized
