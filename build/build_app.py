from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from release_config import (  # type: ignore
        DIST_ROOT,
        EXECUTABLE_NAME,
        GENERATED_ROOT,
        PROJECT_ROOT,
        PYINSTALLER_WORK_ROOT,
        SPEC_PATH,
        WINDOWS_ICON_PATH,
        artifact_directory_name,
        validate_target_os,
    )
    from generate_app_icon import generate_windows_icon  # type: ignore
else:
    from .generate_app_icon import generate_windows_icon
    from .release_config import (
        DIST_ROOT,
        EXECUTABLE_NAME,
        GENERATED_ROOT,
        PROJECT_ROOT,
        PYINSTALLER_WORK_ROOT,
        SPEC_PATH,
        WINDOWS_ICON_PATH,
        artifact_directory_name,
        validate_target_os,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a portable Numeric WorkBench release artifact.",
    )
    parser.add_argument(
        "--os",
        required=True,
        help="Target operating system: windows, linux or macos.",
    )
    return parser.parse_args()


def _run_pyinstaller(target_os: str) -> Path:
    dist_root = DIST_ROOT / target_os
    work_root = PYINSTALLER_WORK_ROOT / target_os
    artifact_name = artifact_directory_name(target_os)
    packaged_root = dist_root / EXECUTABLE_NAME
    final_root = dist_root / artifact_name

    shutil.rmtree(work_root, ignore_errors=True)
    shutil.rmtree(packaged_root, ignore_errors=True)
    shutil.rmtree(final_root, ignore_errors=True)
    dist_root.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(dist_root),
        "--workpath",
        str(work_root),
        str(SPEC_PATH),
    ]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)

    if not packaged_root.exists():
        raise FileNotFoundError(
            f"Expected packaged output at '{packaged_root}'."
        )

    packaged_root.rename(final_root)
    return final_root


def _prepare_build_assets(target_os: str) -> None:
    GENERATED_ROOT.mkdir(parents=True, exist_ok=True)
    if target_os == "windows":
        generate_windows_icon(WINDOWS_ICON_PATH)


def _validate_artifact(final_root: Path) -> None:
    expected_names = {
        f"{EXECUTABLE_NAME}.exe",
        EXECUTABLE_NAME,
        f"{EXECUTABLE_NAME}.app",
    }
    discovered = {path.name for path in final_root.rglob("*")}
    if not expected_names & discovered:
        raise FileNotFoundError(
            "Build finished but no executable/app bundle was found inside "
            f"'{final_root}'."
        )


def main() -> int:
    args = _parse_args()
    target_os = validate_target_os(args.os)
    _prepare_build_assets(target_os)
    final_root = _run_pyinstaller(target_os)
    _validate_artifact(final_root)
    print(final_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
