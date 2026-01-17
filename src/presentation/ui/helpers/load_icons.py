from pathlib import Path
from PySide6.QtGui import QIcon

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

def load_icon(name: str) -> QIcon:
    return QIcon(str(ASSETS_DIR / name))

