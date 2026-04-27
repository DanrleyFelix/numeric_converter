from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="Overview",
    subtitle="A calculator for conversion, expressions, reusable variables and workspace state",
    html="""
        <p>Numeric WorkBench combines a base converter with a command calculator that remembers variables, submitted commands and converter state.</p>
        <h2>Core workflow</h2>
        <ul>
            <li>Use the converter for Decimal, Binary, Hex (BE) and Hex (LE) representations.</li>
            <li>Use the command window for expressions, assignments and variable reuse.</li>
            <li>Use workspace files to save or load the complete context in one action.</li>
            <li>Use <b>Variables</b> and <b>Logs</b> above the command editor to inspect stored assignments and submitted commands in separate windows.</li>
            <li>Load a workspace file to restore variables, logs, the active command line, key panel visibility and converter state.</li>
        </ul>
        <h2>Data location</h2>
        <p>Workspace JSON files are stored in <code>data/workspaces</code>. The automatic default context lives under <code>data/contexts</code>.</p>
    """,
)
