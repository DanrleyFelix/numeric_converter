from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="Environment",
    subtitle="Symbols, labels, regions, file maps and reusable commands",
    html="""
        <p>Environment tools make a binary easier to read, navigate and edit repeatedly.</p>
        <h2>Symbols</h2>
        <ul>
            <li>Symbols accept both <code>_name</code> and <code>@name</code> forms in assembly instructions.</li>
            <li><b>Local Symbols</b> belong to the current file/tab and are shared by all of its versions.</li>
            <li><b>Global Symbols</b> are available to every open tab for the current Binary Workbench session and are not attached to a workspace or version.</li>
            <li>Loading a Symbols JSON merges entries by name; matching names are updated and unrelated symbols remain available.</li>
            <li>Activate an existing symbol row to change its name or value.</li>
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
            <li><code>/sp</code> creates a stack save/restore block. It accepts register groups such as <code>/sp s</code> or <code>/sp s t a v k</code>, and still accepts explicit registers.</li>
            <li><code>/li</code> expands a 32-bit value to <code>lui</code> plus <code>ori</code>. Example: <code>/li 0x801D9200 a0</code>.</li>
            <li><code>/lb</code>, <code>/lbu</code>, <code>/lh</code>, <code>/lhu</code>, <code>/lw</code>, <code>/sb</code>, <code>/sbu</code>, <code>/sh</code>, <code>/shu</code> and <code>/sw</code> load or store by address, optional base/value registers and optional displacement.</li>
            <li><code>/blt</code>, <code>/ble</code>, <code>/bgt</code> and <code>/bge</code> expand to <code>slt</code> plus <code>beq</code> or <code>bne</code>, followed by the required delay-slot <code>nop</code>.</li>
            <li><code>/if</code> accepts compact or spaced comparisons, such as <code>/if t1&lt;t2 loop</code> or <code>/if t1 &lt; t2 loop</code>.</li>
            <li><code>/where</code> creates a branch-only loop structure with a start label, end label, step update and delay-slot <code>nop</code> lines.</li>
            <li>When command registers are omitted, automatic registers use <code>t1</code> through <code>t9</code>; <code>t0</code> is kept for internal <code>slt</code> comparisons.</li>
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
