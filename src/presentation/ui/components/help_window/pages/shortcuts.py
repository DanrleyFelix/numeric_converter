from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="Shortcuts",
    subtitle="Numeric Workbench keyboard shortcuts",
    html="""
        <p>These shortcuts apply to the Numeric Workbench window.</p>
        <h2>Workspace and tools</h2>
        <ul>
            <li><code>Ctrl+S</code>: save the current workspace.</li>
            <li><code>Ctrl+O</code>: load a workspace.</li>
            <li><code>Alt+B</code>: open Binary Workbench.</li>
            <li><code>Alt+G</code>: open Guide.</li>
            <li><code>Alt+D</code>: open Donor.</li>
        </ul>
        <h2>Preferences</h2>
        <ul>
            <li><code>Alt+P</code>: open Preferences &gt; Converter.</li>
            <li><code>Alt+L</code>: open Preferences &gt; Logs.</li>
            <li><code>Alt+S</code>: toggle Show Key Panel.</li>
            <li><code>Alt+X</code>: toggle Auto Convert.</li>
        </ul>
        <h2>Converter and command focus</h2>
        <ul>
            <li><code>Tab</code>: move through Decimal, Binary, Hex (BE), Hex (LE), Command Window and back to Decimal.</li>
            <li><code>F1</code>: focus Decimal.</li>
            <li><code>F2</code>: focus Binary.</li>
            <li><code>F3</code>: focus Hex (BE).</li>
            <li><code>F4</code>: focus Hex (LE).</li>
            <li><code>F5</code>: focus Command Window.</li>
            <li><code>Alt+C</code>: copy the raw value from the focused converter field.</li>
        </ul>
        <h2>Workspace tables</h2>
        <ul>
            <li><code>Alt+V</code>: open the Variables table.</li>
            <li><code>Alt+N</code>: open the Logs table.</li>
        </ul>
    """,
)
