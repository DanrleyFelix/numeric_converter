from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.presentation.ui.components.help_window.pages import HELP_PAGES
from src.presentation.ui.components.help_window.styles import HELP_SCROLLBAR_QSS, render_help_html


class HelpWindow(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("help-window")
        self.setWindowTitle("User Guide")
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setMinimumSize(920, 620)
        self.resize(980, 680)
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(24)
        title = QLabel("User Guide")
        title.setObjectName("help-title")
        root.addWidget(title)
        content = QHBoxLayout()
        content.setSpacing(24)
        self.navigation = QListWidget()
        self.navigation.setObjectName("help-nav")
        self.navigation.setFixedWidth(250)
        self.navigation.setFocusPolicy(Qt.NoFocus)
        self.pages = QStackedWidget()
        self.pages.setObjectName("help-pages")
        for page in HELP_PAGES:
            self.navigation.addItem(QListWidgetItem(page.title))
            self.pages.addWidget(self._build_page(page.title, page.subtitle, page.html))
        content.addWidget(self.navigation)
        content.addWidget(self.pages, 1)
        root.addLayout(content, 1)
        footer = QHBoxLayout()
        footer.setSpacing(14)
        self.previous_button = QPushButton("Previous")
        self.previous_button.setObjectName("help-nav-button")
        self.previous_button.setMinimumSize(120, 38)
        self.next_button = QPushButton("Next")
        self.next_button.setObjectName("help-nav-button")
        self.next_button.setMinimumSize(120, 38)
        self.page_indicator = QLabel()
        self.page_indicator.setObjectName("help-page-indicator")
        self.page_indicator.setAlignment(Qt.AlignCenter)
        footer.addWidget(self.previous_button, 0, Qt.AlignLeft)
        footer.addWidget(self.page_indicator, 1)
        footer.addWidget(self.next_button, 0, Qt.AlignRight)
        root.addLayout(footer)
        self.navigation.currentRowChanged.connect(self._show_page)
        self.previous_button.clicked.connect(self._show_previous)
        self.next_button.clicked.connect(self._show_next)
        self.navigation.setCurrentRow(0)

    def _build_page(self, title: str, subtitle: str, html: str) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        browser = QTextBrowser()
        browser.setObjectName("help-page")
        browser.setOpenExternalLinks(False)
        browser.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        browser.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        browser.document().setDocumentMargin(0)
        browser.verticalScrollBar().setStyleSheet(HELP_SCROLLBAR_QSS)
        browser.setHtml(render_help_html(title, subtitle, html))
        browser.verticalScrollBar().setValue(0)
        layout.addWidget(browser)
        return container

    def _show_page(self, index: int) -> None:
        if index < 0:
            return
        self.pages.setCurrentIndex(index)
        page = self.pages.currentWidget()
        if page is not None:
            browser = page.findChild(QTextBrowser, "help-page")
            if browser is not None:
                browser.verticalScrollBar().setValue(0)
        total = self.pages.count()
        self.page_indicator.setText(f"Page {index + 1} of {total}")
        self.previous_button.setEnabled(index > 0)
        self.next_button.setEnabled(index < total - 1)

    def _show_previous(self) -> None:
        index = self.pages.currentIndex()
        if index > 0:
            self.navigation.setCurrentRow(index - 1)

    def _show_next(self) -> None:
        index = self.pages.currentIndex()
        if index < self.pages.count() - 1:
            self.navigation.setCurrentRow(index + 1)
