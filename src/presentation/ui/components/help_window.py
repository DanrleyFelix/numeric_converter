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
    QVBoxLayout,
    QWidget,
)


HELP_PAGES = [
    {
        "title": "Overview",
        "subtitle": "What Numeric WorkBench does",
        "html": """
            <h1>Numeric WorkBench</h1>
            <p>Numeric WorkBench combines a live numeric converter with a programmable command window.</p>
            <h2>Main ideas</h2>
            <ul>
                <li>Type in decimal, binary, hex big-endian or hex little-endian and the other views update automatically.</li>
                <li>Use the command window to evaluate expressions, create variables and reuse them later.</li>
                <li>Context stores variables and command history. Log stores execution lines and results.</li>
                <li>Everything is persisted in <code>data/contexts</code> and <code>data/logs</code>.</li>
            </ul>
            <h2>Quick flow</h2>
            <ol>
                <li>Enter a value in any converter field or type an expression in the command window.</li>
                <li>Review the converted representations and the command result label.</li>
                <li>Save or load a specific context/log from the File menu whenever needed.</li>
            </ol>
        """,
    },
    {
        "title": "Converter",
        "subtitle": "Working with Decimal, Binary, Hex (BE) and Hex (LE)",
        "html": """
            <h1>Converter</h1>
            <p>Each input accepts only characters that belong to its own numeric base.</p>
            <h2>Accepted input</h2>
            <ul>
                <li><b>Decimal</b>: digits <code>0-9</code>.</li>
                <li><b>Binary</b>: digits <code>0</code> and <code>1</code>.</li>
                <li><b>Hex (BE)</b> and <b>Hex (LE)</b>: digits <code>0-9</code> and letters <code>A-F</code>.</li>
                <li>The cursor always stays at the end so typing and backspace remain predictable.</li>
                <li>Numpad digits are accepted.</li>
            </ul>
            <h2>Zero padding and grouping</h2>
            <ul>
                <li>Raw typed content is preserved separately from formatting.</li>
                <li>Display formatting may prepend zeroes to satisfy zero padding and grouping.</li>
                <li>For hexadecimal values, an extra leading zero is also added when needed to complete a full byte.</li>
                <li>The converted value uses the effective padded representation, not only the raw typed content.</li>
            </ul>
            <h2>Examples</h2>
            <pre>Hex (LE) raw: 45
Displayed with group size 4 + zero pad: 0045
Next key: 4
Raw becomes: 454
Displayed becomes: 0454</pre>
        """,
    },
    {
        "title": "Command Window",
        "subtitle": "Expressions, variables and automatic conversion",
        "html": """
            <h1>Command Window</h1>
            <p>The command window validates while you type and trims invalid trailing content when necessary.</p>
            <h2>You can type</h2>
            <ul>
                <li>Decimal numbers and identifiers compatible with Python variable rules.</li>
                <li>Binary and hexadecimal prefixes like <code>0b1010</code> and <code>0x2A</code>.</li>
                <li>Operators such as <code>+</code>, <code>-</code>, <code>*</code>, <code>/</code>, <code>&amp;</code>, <code>|</code>, <code>^</code>, <code>~</code>, <code>&lt;&lt;</code>, <code>&gt;&gt;</code>, <code>==</code>, <code>!=</code>, <code>&gt;=</code>, <code>&lt;=</code> and textual operators like <code>NOT</code>, <code>AND</code>, <code>OR</code>, <code>XOR</code>.</li>
                <li>Assignments such as <code>mask = 0xFF</code>.</li>
            </ul>
            <h2>Autocomplete</h2>
            <ul>
                <li>Saved variables appear as autocomplete suggestions while you type identifiers.</li>
                <li>The current context is the source for those suggestions.</li>
            </ul>
            <h2>Convert toggle</h2>
            <ul>
                <li>When <b>Convert</b> is active, a successful decimal result is copied into the Decimal input of the converter automatically.</li>
                <li>The command result remains visible in the top label in green.</li>
            </ul>
        """,
    },
    {
        "title": "Context and Logs",
        "subtitle": "Persistence, history, log and key panel behavior",
        "html": """
            <h1>Context and Logs</h1>
            <h2>Context</h2>
            <ul>
                <li>Context stores variables, command history, the active command line and converter state.</li>
                <li>Use <b>File &gt; Save Context</b> and <b>File &gt; Load Context</b> for specific JSON files.</li>
                <li>The application also keeps a default context automatically.</li>
            </ul>
            <h2>Log</h2>
            <ul>
                <li>Log stores execution lines in the form <code>expression -&gt; result</code>.</li>
                <li>Use <b>File &gt; Save Log</b> and <b>File &gt; Load Log</b> for specific JSON files.</li>
                <li>The default log is also saved automatically.</li>
            </ul>
            <h2>Key panel</h2>
            <ul>
                <li><b>LOG</b> toggles the History/Log tab.</li>
                <li><b>CLEAR</b> removes the last character from the command input, or deletes one line from the active History/Log panel.</li>
                <li><b>ENTER</b> submits the current expression.</li>
            </ul>
        """,
    },
    {
        "title": "Preferences",
        "subtitle": "Formatting options and interface behavior",
        "html": """
            <h1>Preferences</h1>
            <p>Use the Preferences menu to control the converter presentation and visibility.</p>
            <h2>Available options</h2>
            <ul>
                <li>Group size per converter field.</li>
                <li>Zero padding per converter field.</li>
                <li>Show or hide the key panel.</li>
            </ul>
            <h2>Tips</h2>
            <ul>
                <li>Use larger binary groups for byte-oriented workflows.</li>
                <li>Use zero padding in hex little-endian when you want aligned byte groups during typing.</li>
                <li>Open this Help window whenever you need the calculator manual inside the app.</li>
            </ul>
        """,
    },
]


class HelpWindow(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("help-window")
        self.setWindowTitle("Help")
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setMinimumSize(920, 620)
        self.resize(980, 680)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        header = QVBoxLayout()
        header.setSpacing(4)

        title = QLabel("Help")
        title.setObjectName("help-title")
        subtitle = QLabel("Manual de uso da Numeric WorkBench")
        subtitle.setObjectName("help-subtitle")

        header.addWidget(title)
        header.addWidget(subtitle)
        root.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(16)

        self.navigation = QListWidget()
        self.navigation.setObjectName("help-nav")
        self.navigation.setFixedWidth(220)

        self.pages = QStackedWidget()
        self.pages.setObjectName("help-pages")

        for page in HELP_PAGES:
            item = QListWidgetItem(page["title"])
            self.navigation.addItem(item)
            self.pages.addWidget(self._build_page(page["title"], page["subtitle"], page["html"]))

        content.addWidget(self.navigation)
        content.addWidget(self.pages, 1)
        root.addLayout(content, 1)

        footer = QHBoxLayout()
        footer.setSpacing(10)

        self.previous_button = QPushButton("Previous")
        self.previous_button.setObjectName("help-nav-button")
        self.next_button = QPushButton("Next")
        self.next_button.setObjectName("help-nav-button")
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
        browser.setHtml(
            f"""
            <html>
                <body style="
                    background-color: #0F0F1E;
                    color: #EAEAF5;
                    font-family: 'Segoe UI';
                    font-size: 14px;
                    line-height: 1.55;
                    padding: 12px;">
                    <div style="
                        border: 1px solid #133874;
                        border-radius: 16px;
                        background-color: #151527;
                        padding: 22px;">
                        <div style="margin-bottom: 18px;">
                            <div style="font-size: 26px; font-weight: 600; color: #EAEAF5;">{title}</div>
                            <div style="font-size: 15px; color: #B5B5C5; margin-top: 4px;">{subtitle}</div>
                        </div>
                        <div>{html}</div>
                    </div>
                </body>
            </html>
            """
        )
        layout.addWidget(browser)
        return container

    def _show_page(self, index: int) -> None:
        if index < 0:
            return

        self.pages.setCurrentIndex(index)
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
