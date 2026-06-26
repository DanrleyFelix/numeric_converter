from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="Environment",
    subtitle="Symbols, labels, regions, file maps and reusable commands",
    html="""
        <p>Environment tools make a binary easier to read, navigate and edit repeatedly.</p>
        <h2>Symbols</h2>
        <ul>
            <li><b>Variables</b> use the <code>_name</code> form and are useful for addresses or offsets that appear in instructions.</li>
            <li><b>Equates</b> use the <code>@name</code> form and are useful for immediate constants.</li>
            <li>Symbols keep source text readable while Raw Instructions shows the resolved values.</li>
        </ul>
        <h2>Labels</h2>
        <ul>
            <li>Labels are detected from assembly rows and can be inspected in one place.</li>
            <li>Jump and branch operands that target labels are clickable, which makes navigation faster.</li>
            <li>A label definition by itself is not a navigation target; the clickable part is the jump or branch destination.</li>
        </ul>
        <h2>Offset Regions</h2>
        <ul>
            <li>Offset Regions name important file areas so you can keep a mental map of the binary.</li>
            <li>Mapped regions are useful when comparing edits, documenting known structures or returning to a relevant range later.</li>
        </ul>
        <h2>LBA File System</h2>
        <ul>
            <li>LBA File System maps named files inside a disc image.</li>
            <li>Internal Files uses this mapping to open one internal file as its own tab.</li>
        </ul>
        <h2>Commands</h2>
        <ul>
            <li>Type commands in Editor Assembly with a leading slash, such as <code>/sp</code>.</li>
            <li><code>/sp</code> creates a stack save/restore block. With no parameters it uses <code>a0 a1 a2 a3 v0 v1</code>.</li>
            <li>You can pass any amount of valid registers to <code>/sp</code>: <code>/sp s0 s1 ra</code>.</li>
            <li>Custom commands are useful for repeated instruction blocks. Register parameters are optional; when provided, they replace matching registers in the saved command in order.</li>
        </ul>
        <h2>Encoding Tables</h2>
        <ul>
            <li>Encoding Tables configure the text table used when decoded text is read from bytes.</li>
            <li>Use a table when a binary stores text with project-specific byte mappings instead of a standard encoding.</li>
            <li>Find can use decoded text searches after the table is available for the active context.</li>
        </ul>
    """,
)
