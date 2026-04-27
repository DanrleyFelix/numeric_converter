from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="Key Panel",
    subtitle="Calculator buttons for the command window",
    html="""
        <p>The key panel writes directly into the command window.</p>
        <h2>Key panel</h2>
        <ul>
            <li><b>CLEAR</b> removes the last character from the command input, or deletes one line from History when the command input is empty.</li>
            <li><b>ENTER</b> submits the current expression.</li>
            <li>Operator, number and prefix buttons insert their text at the current command cursor position.</li>
            <li><b>NOT</b>, <b>AND</b>, <b>OR</b> and <b>XOR</b> add a trailing space automatically.</li>
        </ul>
    """,
)
