from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="Context and Workspace",
    subtitle="Saving variables, logs and the active working state",
    html="""
        <h2>Context</h2>
        <ul>
            <li>Context stores variables, submitted command logs, the active command line, converter state and key panel visibility.</li>
            <li>Use <b>File &gt; Save Workspace</b> and <b>File &gt; Load Workspace</b> to save or load the complete context.</li>
            <li>The default context is saved automatically when the workspace changes.</li>
        </ul>
        <h2>Workspace Windows</h2>
        <ul>
            <li><b>Variables</b> opens the active assignments in a separate table window.</li>
            <li><b>Logs</b> opens successful submitted commands in a separate table window.</li>
            <li>Each row includes a red minus button that removes only that row.</li>
        </ul>
        <h2>Basic to advanced examples</h2>
        <pre>1 + 1 => 2
value=0x10 => 16
value*3 => 48
(value & 0x0F) == 0 => 1</pre>
    """,
)
