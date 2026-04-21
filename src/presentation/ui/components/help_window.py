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


HELP_PAGES = [
    {
        "title": "Overview",
        "subtitle": "A calculator for conversion, expressions, context and logs",
        "html": """
            <h1>Numeric WorkBench</h1>
            <p>Numeric WorkBench combines a base converter with a command calculator that remembers variables, history and logs.</p>
            <h2>Core workflow</h2>
            <ul>
                <li>Use the converter for Decimal, Binary, Hex (BE) and Hex (LE) representations.</li>
                <li>Use the command window for expressions, assignments and variable reuse.</li>
                <li>Use workspace files to save context and log together.</li>
                <li>Load a workspace file to restore variables, history, converter state and execution log in one step.</li>
            </ul>
            <h2>Data location</h2>
            <p>Workspace JSON files are stored in <code>data/workspaces</code>. Automatic defaults still live under <code>data/contexts</code> and <code>data/logs</code>.</p>
        """,
    },
    {
        "title": "Converter",
        "subtitle": "Working with Decimal, Binary, Hex (BE) and Hex (LE)",
        "html": """
            <h1>Converter</h1>
            <p>The converter keeps the typed content separate from the formatted display, so padding and grouping do not corrupt editing.</p>
            <h2>Inputs</h2>
            <ul>
                <li><b>Decimal</b>: digits <code>0-9</code>.</li>
                <li><b>Binary</b>: digits <code>0</code> and <code>1</code>.</li>
                <li><b>Hex (BE)</b> and <b>Hex (LE)</b>: digits <code>0-9</code> and letters <code>A-F</code>.</li>
            </ul>
            <h2>Padding and grouping</h2>
            <ul>
                <li><b>Group size</b> controls how many characters appear in each group.</li>
                <li><b>Zero pad</b> pads the effective input before conversion.</li>
                <li>Hex values with an odd number of digits receive one leading zero to complete a byte.</li>
                <li>Hex (LE) interprets the effective byte sequence as little-endian.</li>
            </ul>
            <h2>Examples</h2>
            <pre>Decimal: 255
Binary: 11111111
Hex (BE): FF
Hex (LE): FF

Hex (LE), group size 4, zero pad enabled:
typed: 45    effective: 0045
typed: 454   effective: 0454</pre>
        """,
    },
    {
        "title": "Command Window",
        "subtitle": "Expressions, variables, operators and automatic conversion",
        "html": """
            <h1>Command Window</h1>
            <p>The command window evaluates expressions and stores variables in the active context.</p>
            <h2>Numbers and variables</h2>
            <ul>
                <li>Decimal numbers: <code>42</code>.</li>
                <li>Binary numbers: <code>0b101010</code>.</li>
                <li>Hexadecimal numbers: <code>0x2A</code>.</li>
                <li>Assignments: <code>mask=0xFF</code> or <code>mask = 0xFF</code>.</li>
                <li>Variable names follow Python identifier rules.</li>
            </ul>
            <h2>Operators</h2>
            <ul>
                <li>Arithmetic: <code>+</code>, <code>-</code>, <code>*</code>, <code>/</code>, <code>%</code>, <code>**</code>.</li>
                <li>Bitwise: <code>&amp;</code>, <code>|</code>, <code>^</code>, <code>~</code>, <code>&lt;&lt;</code>, <code>&gt;&gt;</code>.</li>
                <li>Comparisons: <code>==</code>, <code>!=</code>, <code>&lt;</code>, <code>&gt;</code>, <code>&lt;=</code>, <code>&gt;=</code>.</li>
                <li>Textual aliases: <code>NOT</code>, <code>AND</code>, <code>OR</code>, <code>XOR</code>.</li>
            </ul>
            <h2>Examples</h2>
            <h3>Basic arithmetic</h3>
            <pre>1 + 1
0x10 + 5
0b1010 * 3
(12 + 4) / 2</pre>
            <h3>Assignments and reuse</h3>
            <pre>gp=0x89823A
gp >> 3
offset=0x1C
gp + offset</pre>
            <h3>Bitwise workflows</h3>
            <pre>mask=0xFF
mask AND 0b10101010
flags=0b11001100
flags XOR mask
NOT 0x0F</pre>
            <h3>Comparisons and grouping</h3>
            <pre>value=0x20
(value & 0x0F) == 0
(value + 5) << 2</pre>
            <h2>Autocomplete and Convert</h2>
            <ul>
                <li>Variables saved in the current context appear as autocomplete suggestions.</li>
                <li>When <b>Convert</b> is enabled, a successful non-negative integer result is sent to the Decimal converter input.</li>
            </ul>
        """,
    },
    {
        "title": "Context and Logs",
        "subtitle": "Saving variables, history and execution output",
        "html": """
            <h1>Context and Logs</h1>
            <h2>Context</h2>
            <ul>
                <li>Context stores variables, command history, the active command line and converter state.</li>
                <li>Use <b>File &gt; Save Workspace</b> and <b>File &gt; Load Workspace</b> to save or load context and log together.</li>
                <li>The default context is saved automatically when the workspace changes.</li>
            </ul>
            <h2>Log</h2>
            <ul>
                <li>Log stores execution lines in the form <code>expression -&gt; result</code>.</li>
                <li>The default log is saved automatically after command execution.</li>
            </ul>
            <h2>Basic to advanced examples</h2>
            <pre>1 + 1 -> 2
value=0x10 -> 16
value*3 -> 48
(value & 0x0F) == 0 -> 1</pre>
        """,
    },
    {
        "title": "Key Panel",
        "subtitle": "Calculator buttons for the command window",
        "html": """
            <h1>Key Panel</h1>
            <p>The key panel writes directly into the command window.</p>
            <h2>Key panel</h2>
            <ul>
                <li><b>LOG</b> toggles the History/Log tab.</li>
                <li><b>CLEAR</b> removes the last character from the command input, or deletes one line from the active History/Log panel.</li>
                <li><b>ENTER</b> submits the current expression.</li>
            </ul>
            <h2>Typical use</h2>
            <pre>0x FF AND 0b 1010 ENTER
LOG
CLEAR</pre>
        """,
    },
    {
        "title": "Preferences",
        "subtitle": "Converter formatting and key panel visibility",
        "html": """
            <h1>Preferences</h1>
            <p>Preferences configure converter display rules and key panel visibility.</p>
            <h2>Converter options</h2>
            <ul>
                <li><b>Group size</b>: controls visual grouping for each converter field.</li>
                <li><b>Zero pad</b>: pads the effective value before formatting and conversion.</li>
            </ul>
            <h2>Interface options</h2>
            <ul>
                <li><b>Show Key Panel</b>: toggles the calculator button panel.</li>
            </ul>
            <h2>Example configuration</h2>
            <pre>Decimal: group size 3, zero pad off
Binary: group size 8, zero pad on
Hex (BE): group size 2, zero pad off
Hex (LE): group size 4, zero pad on</pre>
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
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(20)

        header = QVBoxLayout()
        header.setSpacing(4)

        title = QLabel("Help")
        title.setObjectName("help-title")
        subtitle = QLabel("Numeric WorkBench user guide")
        subtitle.setObjectName("help-subtitle")

        header.addWidget(title)
        header.addWidget(subtitle)
        root.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(20)

        self.navigation = QListWidget()
        self.navigation.setObjectName("help-nav")
        self.navigation.setFixedWidth(240)
        self.navigation.setFocusPolicy(Qt.NoFocus)

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
        footer.setSpacing(14)

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
        layout.setContentsMargins(6, 6, 6, 6)

        browser = QTextBrowser()
        browser.setObjectName("help-page")
        browser.setOpenExternalLinks(False)
        browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        browser.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        browser.document().setDocumentMargin(18)
        browser.setHtml(
            f"""
            <html>
                <head>
                    <style>
                        h1, h2, h3, p, li {{
                            white-space: normal;
                        }}
                        pre {{
                            background-color: #0F0F1E;
                            border: 1px solid #133874;
                            border-radius: 10px;
                            color: #EAEAF5;
                            padding: 12px;
                            white-space: pre-wrap;
                            word-wrap: break-word;
                        }}
                        code {{
                            color: #EAEAF5;
                            white-space: normal;
                        }}
                    </style>
                </head>
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
