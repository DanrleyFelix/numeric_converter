from PySide6.QtWidgets import QMainWindow
from src.presentation.ui.components.numeric_workbench import NumericWorkbench
from src.presentation.ui.design.icons import Icons


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Numeric Workbench")
        self.setWindowIcon(Icons.numeric_workbench())

        self.workbench = NumericWorkbench()
        self.setCentralWidget(self.workbench)

    def render(self, vm):
        self.workbench.render(vm)
