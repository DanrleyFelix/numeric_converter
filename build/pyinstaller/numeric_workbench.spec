# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from sys import platform as sys_platform

from build.pyinstaller_inputs import (
    EXCLUDED_MODULES,
    collect_packaged_data,
    filter_packaged_entries,
)

project_root = Path.cwd().resolve()
generated_icon = project_root / "build" / "generated" / "app.ico"
datas = collect_packaged_data(project_root)

analysis = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=list(EXCLUDED_MODULES),
    noarchive=False,
    optimize=0,
)
filtered_binaries = filter_packaged_entries(analysis.binaries)
filtered_datas = filter_packaged_entries(analysis.datas)
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
        filtered_binaries,
        filtered_datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="NumericWorkBench",
    )
else:
    coll = COLLECT(
        exe,
        filtered_binaries,
        filtered_datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="NumericWorkBench",
    )
