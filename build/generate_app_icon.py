from __future__ import annotations

import os
import struct
import sys
import subprocess
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.presentation.ui.design.icon_font import resolve_fontawesome_solid_path
from src.presentation.ui.design.icon_specs import ICON_GLYPHS, WINDOW_ICON_NAME, WINDOW_ICON_TOKEN
from src.presentation.ui.helpers.load_qss import THEME_TOKENS

ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
FONT_AWESOME_SOLID = resolve_fontawesome_solid_path()
POWERSHELL_RENDERER = PROJECT_ROOT / "build" / "render_fontawesome_icon.ps1"


def _fontawesome_glyph() -> str:
    return ICON_GLYPHS[WINDOW_ICON_NAME]


def _icon_hex_color() -> str:
    color = THEME_TOKENS[WINDOW_ICON_TOKEN]
    if not color.startswith("#") or len(color) not in (7, 9):
        raise ValueError(f"Unsupported icon color '{color}'.")
    return color[:7]


def _render_png_payload_windows(size: int) -> bytes:
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / f"icon-{size}.png"
        command = [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(POWERSHELL_RENDERER),
            "-FontPath",
            str(FONT_AWESOME_SOLID),
            "-Glyph",
            _fontawesome_glyph(),
            "-CanvasSize",
            str(size),
            "-HexColor",
            _icon_hex_color(),
            "-OutputPath",
            str(output),
        ]
        subprocess.run(command, cwd=PROJECT_ROOT, check=True)
        return output.read_bytes()


def _build_ico_payload(images: list[tuple[int, bytes]]) -> bytes:
    header = struct.pack("<HHH", 0, 1, len(images))
    directory = bytearray()
    payload = bytearray()
    offset = 6 + (16 * len(images))

    for size, png_bytes in images:
        width = 0 if size >= 256 else size
        height = 0 if size >= 256 else size
        directory.extend(
            struct.pack(
                "<BBBBHHII",
                width,
                height,
                0,
                0,
                1,
                32,
                len(png_bytes),
                offset,
            )
        )
        payload.extend(png_bytes)
        offset += len(png_bytes)

    return bytes(header + directory + payload)


def generate_windows_icon(target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    images = [(size, _render_png_payload_windows(size)) for size in ICON_SIZES]
    target.write_bytes(_build_ico_payload(images))
    return target
