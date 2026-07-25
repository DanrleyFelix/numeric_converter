"""Binary Workbench Guide page for debugger assembly directives."""

from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="Debugger Directives",
    subtitle="Prepare assembly, imports, registers and virtual memory for debugging",
    html="""
        <p>Debugger directives are written in <b>Editor Assembly</b> before or among the instructions. They configure the debug session and do not generate instruction bytes.</p>
        <h2>Virtual memory</h2>
        <p>Virtual memory is the isolated address range that the debugger makes available to the emulated program. It connects file content to runtime addresses and defines where code, data and the stack may be read or written. A correct range is essential: an address outside it produces an invalid-memory-access event instead of silently corrupting data.</p>
        <pre>* virtual_memory_range 0x80000000 0x801FFFFF</pre>
        <p>The first and last addresses are inclusive. Choose a range that contains every imported block and the complete stack area used by the program.</p>
        <h2>Import</h2>
        <p><code>import</code> loads binary content into virtual memory at a runtime address. Use the current Binary Workbench file or an imported project file, then confirm that the destination lies inside <code>virtual_memory_range</code>.</p>
        <pre>* import current_file 0x80000000</pre>
        <h2>Define</h2>
        <p><code>define</code> establishes an initial register value. It is commonly used for the program counter, stack pointer and arguments.</p>
        <pre>* define $pc 0x80000000
* define $sp 0x801FFFF0
* define $a0 0x2</pre>
        <h2>Ignore</h2>
        <p><code>ignore</code> marks a runtime instruction address as ignored by the debugger flow. It is useful for known calls or branches that should not be followed in the current investigation.</p>
        <pre>* ignore $pc 0x80024D34</pre>
        <h2>Before opening the Debugger</h2>
        <ul>
            <li>Keep addresses hexadecimal and inside the configured virtual-memory range.</li>
            <li>Import every block that the program will execute or access.</li>
            <li>Define <code>$pc</code> at a loaded instruction and place <code>$sp</code> inside writable virtual memory.</li>
            <li>Review directive errors in Debug Log; invalid directives are reported without becoming assembly instructions.</li>
        </ul>
    """,
)
