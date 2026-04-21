import sys
from PySide6.QtWidgets import QApplication
from src.main import create_main_window

def main():
    app = QApplication(sys.argv)
    view = create_main_window()

    view.show()
    sys.exit(app.exec())
    
if __name__ == "__main__":
    main()
