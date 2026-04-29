import sys

from PySide6.QtWidgets import QApplication

from src.main import create_main_window


def main() -> int:
    app = QApplication(sys.argv)
    window = create_main_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
