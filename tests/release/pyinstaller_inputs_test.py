from build.pyinstaller_inputs import (
    EXCLUDED_BINARY_NAMES,
    EXCLUDED_MODULES,
    collect_packaged_data,
    filter_packaged_entries,
)
from build.release_config import PROJECT_ROOT


def test_collect_packaged_data_includes_project_resources():
    data_entries = collect_packaged_data(PROJECT_ROOT)
    mapped_targets = {target for _, target in data_entries}
    style_component_targets = {
        target
        for source, target in data_entries
        if source.endswith("components\\base.qss") or source.endswith("components/base.qss")
    }

    assert "data" in mapped_targets
    assert "src/presentation/ui/design/style" in mapped_targets
    assert "assets/fonts" in mapped_targets
    assert "src/presentation/ui/design/style/components" in style_component_targets


def test_filter_packaged_entries_removes_excluded_binary_names():
    entries = [
        ("PySide6/Qt6Widgets.dll", "C:/bundle/PySide6/Qt6Widgets.dll", "BINARY"),
        ("PySide6/Qt6Quick.dll", "C:/bundle/PySide6/Qt6Quick.dll", "BINARY"),
    ]

    filtered = filter_packaged_entries(entries)

    assert filtered == [entries[0]]


def test_filter_packaged_entries_removes_excluded_runtime_paths():
    entries = [
        ("win32com/__init__.py", "C:/Python/win32com/__init__.py", "DATA"),
        ("src/presentation/ui/design/style/main.qss", "C:/app/style/main.qss", "DATA"),
    ]

    filtered = filter_packaged_entries(entries)

    assert filtered == [entries[1]]


def test_excluded_modules_cover_qt_quick_pdf_opengl_stacks():
    expected_modules = {
        "PySide6.QtNetwork",
        "PySide6.QtQuick",
        "PySide6.QtQml",
        "PySide6.QtPdf",
        "PySide6.QtOpenGL",
    }

    assert expected_modules.issubset(set(EXCLUDED_MODULES))
    assert "Qt6Quick.dll" in EXCLUDED_BINARY_NAMES
    assert "opengl32sw.dll" in EXCLUDED_BINARY_NAMES
