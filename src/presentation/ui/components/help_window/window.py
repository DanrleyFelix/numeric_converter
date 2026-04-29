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

from src.presentation.ui.components.help_window.constants import (
    HELP_WINDOW_MARGIN,
    HELP_WINDOW_SIZE,
    HELP_WINDOW_SPACING,
    HELP_WINDOW_TEXT,
)
from src.presentation.ui.components.help_window.pages import HELP_PAGES
from src.presentation.ui.components.help_window.styles import render_help_html


class HelpWindow(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("help-window")
        self.setWindowTitle(HELP_WINDOW_TEXT.TITLE)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setMinimumSize(HELP_WINDOW_SIZE.MIN_WIDTH, HELP_WINDOW_SIZE.MIN_HEIGHT)
        self.resize(HELP_WINDOW_SIZE.DEFAULT_WIDTH, HELP_WINDOW_SIZE.DEFAULT_HEIGHT)
        root = QVBoxLayout(self)
        root.setContentsMargins(
            HELP_WINDOW_MARGIN.ROOT_LEFT,
            HELP_WINDOW_MARGIN.ROOT_TOP,
            HELP_WINDOW_MARGIN.ROOT_RIGHT,
            HELP_WINDOW_MARGIN.ROOT_BOTTOM,
        )
        root.setSpacing(HELP_WINDOW_SPACING.ROOT)
        title = QLabel(HELP_WINDOW_TEXT.TITLE)
        title.setObjectName("help-title")
        root.addWidget(title)
        content = QHBoxLayout()
        content.setSpacing(HELP_WINDOW_SPACING.CONTENT)
        self.navigation = QListWidget()
        self.navigation.setObjectName("help-nav")
        self.navigation.setFixedWidth(HELP_WINDOW_SIZE.NAVIGATION_WIDTH)
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
        footer.setSpacing(HELP_WINDOW_SPACING.FOOTER)
        self.previous_button = QPushButton(HELP_WINDOW_TEXT.PREVIOUS)
        self.previous_button.setObjectName("help-nav-button")
        self.previous_button.setMinimumSize(
            HELP_WINDOW_SIZE.NAV_BUTTON_WIDTH,
            HELP_WINDOW_SIZE.NAV_BUTTON_HEIGHT,
        )
        self.next_button = QPushButton(HELP_WINDOW_TEXT.NEXT)
        self.next_button.setObjectName("help-nav-button")
        self.next_button.setMinimumSize(
            HELP_WINDOW_SIZE.NAV_BUTTON_WIDTH,
            HELP_WINDOW_SIZE.NAV_BUTTON_HEIGHT,
        )
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
        layout.setContentsMargins(
            HELP_WINDOW_MARGIN.PAGE_LEFT,
            HELP_WINDOW_MARGIN.PAGE_TOP,
            HELP_WINDOW_MARGIN.PAGE_RIGHT,
            HELP_WINDOW_MARGIN.PAGE_BOTTOM,
        )
        browser = QTextBrowser()
        browser.setObjectName("help-page")
        browser.setOpenExternalLinks(False)
        browser.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        browser.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        browser.setViewportMargins(0, 0, HELP_WINDOW_MARGIN.VIEWPORT_RIGHT_GUTTER, 0)
        browser.document().setDocumentMargin(0)
        browser.verticalScrollBar().setObjectName(HELP_WINDOW_TEXT.PAGE_SCROLLBAR_OBJECT_NAME)
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
        self.page_indicator.setText(
            HELP_WINDOW_TEXT.PAGE_TEMPLATE.format(current=index + 1, total=total)
        )
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
