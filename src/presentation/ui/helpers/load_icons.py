from PySide6.QtGui import QIcon

from src.main.resource_paths import icons_root

def load_icon(name: str) -> QIcon:
    return QIcon(str(icons_root() / name))

