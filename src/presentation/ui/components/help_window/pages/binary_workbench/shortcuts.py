from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="Shortcuts",
    subtitle="Binary Workbench keyboard shortcuts",
    html="""
        <p>These shortcuts apply to Binary Workbench and its editor panes.</p>
        <h2>File and versions</h2>
        <ul>
            <li><code>Ctrl+O</code>: open file.</li>
            <li><code>Ctrl+N</code>: create New Scratch Code.</li>
            <li><code>Alt+I</code>: open Internal Files.</li>
            <li><code>Alt+V</code>: open Version.</li>
            <li><code>Alt+S</code>: update the current version.</li>
            <li><code>Ctrl+S</code>: save file.</li>
        </ul>
        <h2>Search and selection</h2>
        <ul>
            <li><code>Ctrl+G</code>: open Go to.</li>
            <li><code>Ctrl+F</code>: open Find.</li>
            <li><code>Ctrl+E</code>: open Select Block.</li>
            <li><code>Ctrl+A</code>: select all content in the active editor surface.</li>
        </ul>
        <h2>Editor movement and repeated edits</h2>
        <ul>
            <li><code>Alt+Up</code> / <code>Alt+Down</code>: move the current assembly line.</li>
            <li><code>Ctrl+Shift+Up</code> / <code>Ctrl+Shift+Down</code>: duplicate selected assembly lines.</li>
            <li><code>Page Up</code>: load the next Editor Assembly page from the line after the current viewport.</li>
            <li><code>Page Down</code>: return one Editor Assembly page, or to the first line when fewer lines exist above.</li>
            <li><code>Ctrl+D</code>: add the next occurrence to the multi-selection.</li>
            <li><code>Ctrl+Q</code>: move the occurrence selection to the next occurrence only.</li>
            <li><code>Alt+Click</code>: add another cursor in Editor Assembly or Bytes.</li>
            <li><code>Esc</code>: clear occurrence selections.</li>
        </ul>
        <h2>Immediate helpers and editing</h2>
        <ul>
            <li><code>Alt+W</code>: create a Variable from the immediate under the cursor.</li>
            <li><code>Alt+E</code>: create an Equate from the immediate under the cursor.</li>
            <li><code>Alt+K</code>: create a custom Command from selected assembly instructions.</li>
            <li><code>Alt+J</code>: open the label under the cursor in a new tab.</li>
            <li><code>Ctrl+C</code>, <code>Ctrl+X</code>, <code>Ctrl+V</code>: copy, cut and paste in the active editor.</li>
            <li><code>Ctrl+Z</code> / <code>Ctrl+Y</code>: undo and redo.</li>
            <li><code>Enter</code> or <code>Tab</code>: accept the current autocomplete suggestion.</li>
        </ul>
    """,
)
