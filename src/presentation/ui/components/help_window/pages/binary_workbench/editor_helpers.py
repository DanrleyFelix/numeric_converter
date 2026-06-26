from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="Editor Helpers",
    subtitle="Immediate symbols, custom commands and repeated edit tools",
    html="""
        <p>Editor helpers keep repeated assembly edits close to the Editor Assembly surface.</p>
        <h2>Immediate symbols</h2>
        <ul>
            <li><code>Alt+W</code> creates a Variable from the immediate value under the cursor.</li>
            <li><code>Alt+E</code> creates an Equate from the immediate value under the cursor.</li>
            <li>The context menu offers the same actions when an immediate value is available.</li>
        </ul>
        <h2>Custom commands</h2>
        <ul>
            <li><code>Alt+K</code> creates a custom Command from selected assembly instructions.</li>
            <li>Saved commands can be typed later in Editor Assembly with a leading slash.</li>
            <li>Command parameters can replace matching registers in the saved instruction block.</li>
        </ul>
        <h2>Repeated edits</h2>
        <ul>
            <li><code>Ctrl+D</code> adds the next occurrence to the current multi-selection.</li>
            <li><code>Ctrl+Q</code> moves the occurrence selection to the next match only.</li>
            <li><code>Esc</code> clears occurrence selections and returns the editor to normal cursor editing.</li>
        </ul>
    """,
)
