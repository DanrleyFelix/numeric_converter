"""Binary Workbench Guide page for the debugger window."""

from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="Debugger Window",
    subtitle="Control execution, inspect runtime state and manage breakpoints",
    html="""
        <h2>Toolbar actions and shortcuts</h2>
        <ul>
            <li><b>Run (F5)</b> starts or continues execution. After Stop, it starts a new session.</li>
            <li><b>Pause (F6)</b> pauses automatic execution.</li>
            <li><b>Stop (F7)</b> ends the current session and invalidates its execution state.</li>
            <li><b>Restart (F8)</b> restores initial memory, applies register values declared by <code>define</code>, sets every other register to zero and leaves the session in <code>READY</code>.</li>
            <li><b>Step (F9)</b> executes the current instruction and pauses at the next one.</li>
            <li><b>Step Over (F10)</b> treats a normal instruction like Step, but runs through a <code>jal</code>/<code>jalr</code> call and its delay slot until control returns.</li>
            <li><b>Config (F11)</b> opens the execution and Debug Log options.</li>
        </ul>
        <h2>Restart and register editing</h2>
        <p>After Restart, registers may be edited while the session is <code>READY</code>; they may also be edited while execution is paused. Run, Step and Step Over continue from the edited PC and register values without resetting them again. A second Restart discards manual edits and restores the declared values and zeros. <code>$zero</code> always remains zero, while breakpoints, <code>IGNORED</code> instructions and Debugger configuration are preserved.</p>
        <h2>Debugger Config</h2>
        <p><code>Interval (ms)</code> is the delay between automatic instruction steps. Use <code>0</code> for the fastest possible execution; <code>2000</code> means one instruction every two seconds. Execution, Memory, Info, Warning and Error determine which event categories appear in Debug Log and are initially checked.</p>
        <h2>The three panels</h2>
        <ul>
            <li><b>Instructions</b> shows addresses, bytes, decoded instructions, origin and persistent execution or breakpoint status.</li>
            <li><b>Reg</b> shows hexadecimal and decimal register values. While paused, edit either value and the other representation is updated automatically.</li>
            <li><b>Runtime panel</b> contains Stack View, Memory View, Breakpoints and Debug Log.</li>
        </ul>
        <h2>Adding breakpoints</h2>
        <ul>
            <li>In Instructions, use <b>Toggle Breakpoint</b> to add or remove an execution breakpoint at that row.</li>
            <li>In Reg, use <b>Add Breakpoint</b> or <code>Alt+B</code> and enter a condition such as <code>$s2 == 0x2</code> or <code>$a3 &gt;= 0x2 or $t3 == 0x0</code>.</li>
            <li>In Breakpoints, type a hexadecimal address and press Enter. Edit Type to <code>w</code>, <code>r</code>, <code>exec</code>, <code>reg</code> or an address combination such as <code>w | r</code>.</li>
            <li>Address types use a hexadecimal WHERE value; <code>reg</code> uses a register condition. A hit pauses execution, and <code>F5</code> continues it.</li>
        </ul>
        <h2>Runtime tabs</h2>
        <ul>
            <li><b>Stack View</b> presents stack offsets, addresses and hexadecimal/decimal values.</li>
            <li><b>Memory View</b> presents grouped bytes across the virtual range. <b>Follow W</b> follows writes and <b>Follow R</b> follows reads.</li>
            <li><b>Breakpoints</b> searches, enables, disables, edits and removes execution, read, write or register breakpoints.</li>
            <li><b>Debug Log</b> records execution, memory and diagnostic events. Search Log filters visible text, while F11 controls visible event categories.</li>
        </ul>
    """,
)
