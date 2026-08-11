from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build.generate_app_icon import generate_windows_icon
from build.pyinstaller_inputs import collect_packaged_binaries
from build.release_config import (
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
from build.validation import (
    disable_incompatible_control_flow_guard,
    sanitized_build_environment,
    validate_build_environment,
    validate_windows_artifact,
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


DEBUGGER_SMOKE_ARGUMENT = "--build-smoke-debugger"
DEBUGGER_SMOKE_TIMEOUT_SECONDS = 15
DEBUGGER_SMOKE_TRACE_ENVIRONMENT = "NUMERIC_WORKBENCH_SMOKE_TRACE"


def _run_pyinstaller(target_os: str) -> Path:
    """Build one clean artifact with a sanitized native-library search path."""

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
    subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=True,
        env=sanitized_build_environment(PROJECT_ROOT),
    )

    if not packaged_root.exists():
        raise FileNotFoundError(
            f"Expected packaged output at '{packaged_root}'."
        )

    packaged_root.rename(final_root)
    return final_root


def _prepare_build_assets(target_os: str) -> None:
    """Generate platform-specific assets needed by the release bundle."""

    GENERATED_ROOT.mkdir(parents=True, exist_ok=True)
    if target_os == "windows":
        generate_windows_icon(WINDOWS_ICON_PATH)


def _validate_artifact(
    final_root: Path,
    target_os: str | None = None,
    native_entries: tuple[tuple[str, str], ...] = (),
) -> None:
    """Require the executable and validate native Windows dependencies."""

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
    if target_os == "windows":
        validate_windows_artifact(final_root, native_entries)


def _run_packaged_debugger_smoke(final_root: Path) -> None:
    """Run the packaged F5 execution path and reject hangs or native crashes."""

    executable = final_root / f"{EXECUTABLE_NAME}.exe"
    trace_path = final_root / ".debugger-smoke-trace"
    trace_path.unlink(missing_ok=True)
    environment = sanitized_build_environment(PROJECT_ROOT)
    environment[DEBUGGER_SMOKE_TRACE_ENVIRONMENT] = str(trace_path)
    try:
        completed = subprocess.run(
            [str(executable), DEBUGGER_SMOKE_ARGUMENT],
            cwd=final_root,
            capture_output=True,
            text=True,
            timeout=DEBUGGER_SMOKE_TIMEOUT_SECONDS,
            check=False,
            env=environment,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            f"Packaged debugger smoke test exceeded {DEBUGGER_SMOKE_TIMEOUT_SECONDS}s."
        ) from error
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout or "no diagnostic output").strip()
        stages = trace_path.read_text(encoding="utf-8") if trace_path.exists() else "none"
        raise RuntimeError(
            "Packaged debugger smoke test failed with exit code "
            f"{completed.returncode}: {details}; completed stages: {stages.strip()}"
        )
    trace_path.unlink(missing_ok=True)


def main() -> int:
    """Validate, build, inspect, and execute one release artifact."""

    args = _parse_args()
    target_os = validate_target_os(args.os)
    native_entries = tuple(collect_packaged_binaries())
    validate_build_environment(
        target_os,
        PROJECT_ROOT / "requirements-build.txt",
        native_entries,
    )
    _prepare_build_assets(target_os)
    final_root = _run_pyinstaller(target_os)
    if target_os == "windows":
        disable_incompatible_control_flow_guard(
            final_root / f"{EXECUTABLE_NAME}.exe"
        )
    _validate_artifact(final_root, target_os, native_entries)
    if target_os == "windows":
        _run_packaged_debugger_smoke(final_root)
    print(final_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
