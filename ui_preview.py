from dataclasses import dataclass
from typing import List, Optional
import sys
from PySide6.QtWidgets import QApplication
from src.presentation.ui.main_window import MainWindow 
from src.presentation.ui.utils import STYLESHEET
from src.presentation.ui.design.icons import Icons


@dataclass(frozen=True)
class DummyViewModel:
    input_text: str
    input_enabled: bool
    can_undo: bool
    can_redo: bool
    log_visible: bool
    log_entries: List[str]
    temp_message: Optional[str] = None


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    view = MainWindow()

    #view.setWindowIcon(Icons.numeric_workbench())
    view.resize(1280, 720)

    preview_vm = DummyViewModel(
        input_text="0xFF + 1",
        input_enabled=True,
        can_undo=True,
        can_redo=False,
        log_visible=True,
        log_entries=[
            "0xFF + 1 = 256",
            "Invalid token at position 3",
            "42 -> 0b101010"],
        temp_message="Invalid expression")

    view.render(preview_vm)
    view.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
