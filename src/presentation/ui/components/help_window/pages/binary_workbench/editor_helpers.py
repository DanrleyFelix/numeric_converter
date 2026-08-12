from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="Editor Helpers",
    subtitle="Immediate symbols, custom commands and repeated edit tools",
    html="""
        <p>Editor helpers keep repeated assembly edits close to the Editor Assembly surface.</p>
        <h2>Immediate symbols</h2>
        <ul>
            <li><code>Alt+W</code> creates a Symbol from the immediate value under the cursor.</li>
            <li>The context menu offers the same action when an immediate value is available.</li>
            <li>Click a symbol in Editor Assembly to change its name or value. For a symbol used by <code>j</code> or <code>jal</code>, use <code>Ctrl+Click</code> because normal click navigates to the resolved target.</li>
        </ul>
        <h2>Short instructions</h2>
        <ul>
            <li>Destination instructions can omit a repeated source register when it can be inferred. For example, <code>addiu $a0, 0x5</code> becomes <code>addiu $a0, $a0, 0x5</code>.</li>
            <li>Register forms work the same way: <code>and $s0, $a0</code> becomes <code>and $s0, $s0, $a0</code>.</li>
            <li>Editor Assembly keeps the short form while Raw Instructions shows the complete instruction used by the assembler.</li>
            <li><code>negu $a0, $t3</code> is a pseudo-instruction for <code>subu $a0, $zero, $t3</code>. Raw Instructions always shows the canonical <code>subu</code> form.</li>
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
