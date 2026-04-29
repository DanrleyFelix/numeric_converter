# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from sys import platform as sys_platform

from PyInstaller.utils.hooks import collect_data_files

project_root = Path.cwd().resolve()
generated_icon = project_root / "build" / "generated" / "app.ico"
qtawesome_datas = collect_data_files("qtawesome")
datas = [
    (str(project_root / "data"), "data"),
    (
        str(project_root / "src" / "presentation" / "ui" / "design" / "style"),
        "src/presentation/ui/design/style",
    ),
]
datas += qtawesome_datas

analysis = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="NumericWorkBench",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=str(generated_icon) if sys_platform == "win32" else None,
)

if sys_platform == "darwin":
    bundle = BUNDLE(
        exe,
        name="NumericWorkBench.app",
        icon=None,
        bundle_identifier="com.numericworkbench.app",
    )
    coll = COLLECT(
        bundle,
        analysis.binaries,
        analysis.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="NumericWorkBench",
    )
else:
    coll = COLLECT(
        exe,
        analysis.binaries,
        analysis.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="NumericWorkBench",
    )
