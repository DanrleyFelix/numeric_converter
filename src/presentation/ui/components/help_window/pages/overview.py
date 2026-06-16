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
            <li>Load a workspace file to restore variables, logs, the active command line and converter state.</li>
        </ul>
        <h2>Data location</h2>
        <p>Numeric context lives under <code>data/numeric_workbench/contexts</code>, preferences under <code>data/numeric_workbench/preferences.json</code>, and Binary Workbench manifests under <code>data/binary_workbench/workspaces</code>.</p>
        <h2>Application shortcuts</h2>
        <ul>
            <li><code>Ctrl+S</code>: save workspace.</li>
            <li><code>Ctrl+O</code>: load workspace.</li>
            <li><code>Alt+B</code>: open Binary Workbench.</li>
            <li><code>Alt+G</code>: open Guide.</li>
            <li><code>Alt+D</code>: open Donor.</li>
            <li><code>Alt+V</code>: open Variables table.</li>
            <li><code>Alt+N</code>: open Logs table.</li>
        </ul>
    """,
)
