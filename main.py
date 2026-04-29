import sys

from PySide6.QtWidgets import QApplication

from src.main import create_main_window
from src.main.runtime_defaults import configure_application_defaults


def main() -> int:
    app = QApplication(sys.argv)
    configure_application_defaults(app)
    window = create_main_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
