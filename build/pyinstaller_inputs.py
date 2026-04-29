from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Iterable

from src.presentation.ui.design.icon_specs import FONT_AWESOME_SOLID_FILENAME

PACKAGED_DIRECTORIES = (
    (Path("data"), "data"),
    (
        Path("src") / "presentation" / "ui" / "design" / "style",
        "src/presentation/ui/design/style",
    ),
)
EXCLUDED_MODULES = (
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetwork",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtDataVisualization",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "PySide6.QtVirtualKeyboard",
    "Pythonwin",
    "win32com",
    "win32com.client",
    "pywin32_system32",
    "tkinter",
    "unittest",
    "test",
)
EXCLUDED_BINARY_NAMES = {
    "Qt6DataVisualization.dll",
    "Qt6OpenGL.dll",
    "Qt6OpenGLWidgets.dll",
    "Qt6Pdf.dll",
    "Qt6Qml.dll",
    "Qt6QmlMeta.dll",
    "Qt6QmlModels.dll",
    "Qt6QmlWorkerScript.dll",
    "Qt6Quick.dll",
    "Qt6Svg.dll",
    "Qt6VirtualKeyboard.dll",
    "QtDataVisualization.pyd",
    "QtOpenGL.pyd",
    "QtOpenGLWidgets.pyd",
    "qpdf.dll",
    "qcertonlybackend.dll",
    "qdirect2d.dll",
    "qgif.dll",
    "qicns.dll",
    "qico.dll",
    "qjpeg.dll",
    "qmodernwindowsstyle.dll",
    "qnetworklistmanager.dll",
    "qoffscreen.dll",
    "qopensslbackend.dll",
    "qschannelbackend.dll",
    "qsvg.dll",
    "qsvgicon.dll",
    "qtga.dll",
    "qtiff.dll",
    "qtvirtualkeyboardplugin.dll",
    "qwbmp.dll",
    "qwebp.dll",
    "libcrypto-1_1.dll",
    "libcrypto-3-x64.dll",
    "libssl-1_1.dll",
    "libssl-3-x64.dll",
    "opengl32sw.dll",
    "Qt6Network.dll",
    "QtNetwork.pyd",
}
EXCLUDED_PATH_FRAGMENTS = (
    "Pythonwin",
    "pywin32_system32",
    "win32com",
)


def collect_packaged_data(project_root: Path) -> list[tuple[str, str]]:
    data_entries: list[tuple[str, str]] = []
    for source_root, target_root in PACKAGED_DIRECTORIES:
        absolute_root = project_root / source_root
        if not absolute_root.exists():
            continue
        data_entries.extend(_collect_directory_files(absolute_root, target_root))
    data_entries.extend(_collect_icon_font_files())
    return data_entries


def filter_packaged_entries(entries: Iterable[tuple]) -> list[tuple]:
    filtered_entries: list[tuple] = []
    for entry in entries:
        serialized = " ".join(str(part) for part in entry)
        basename_set = {
            Path(str(part)).name
            for part in entry
            if isinstance(part, (str, Path))
        }
        if any(fragment in serialized for fragment in EXCLUDED_PATH_FRAGMENTS):
            continue
        if basename_set & EXCLUDED_BINARY_NAMES:
            continue
        filtered_entries.append(entry)
    return filtered_entries


def _collect_directory_files(
    source_root: Path,
    target_root: str,
) -> list[tuple[str, str]]:
    data_entries: list[tuple[str, str]] = []
    for path in sorted(source_root.rglob("*")):
        if not path.is_file():
            continue
        relative_parent = path.relative_to(source_root).parent
        destination = target_root
        if relative_parent != Path("."):
            destination = f"{target_root}/{relative_parent.as_posix()}"
        data_entries.append((str(path), destination))
    return data_entries


def _collect_icon_font_files() -> list[tuple[str, str]]:
    package_root = _resolve_package_root("qtawesome")
    font_path = package_root / "fonts" / FONT_AWESOME_SOLID_FILENAME
    return [(str(font_path), "assets/fonts")]


def _resolve_package_root(package_name: str) -> Path:
    package_spec = importlib.util.find_spec(package_name)
    if package_spec is None or package_spec.origin is None:
        raise ModuleNotFoundError(
            f"Unable to resolve package root for '{package_name}'."
        )
    return Path(package_spec.origin).resolve().parent
