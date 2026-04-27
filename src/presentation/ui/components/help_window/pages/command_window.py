from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="Command Window",
    subtitle="Expressions, variables, operators and automatic conversion",
    html="""
        <p>The command window evaluates expressions and stores variables in the active context.</p>
        <h2>Numbers and variables</h2>
        <ul>
            <li>Decimal numbers: <code>42</code>.</li>
            <li>Binary numbers: <code>0b101010</code>.</li>
            <li>Hexadecimal numbers: <code>0x2A</code>.</li>
            <li>Assignments: <code>mask=0xFF</code> or <code>mask = 0xFF</code>.</li>
            <li>Variable names follow Python identifier rules.</li>
        </ul>
        <h2>Operators</h2>
        <ul>
            <li>Arithmetic: <code>+</code>, <code>-</code>, <code>*</code>, <code>/</code>, <code>%</code>, <code>**</code>.</li>
            <li>Bitwise: <code>&amp;</code>, <code>|</code>, <code>^</code>, <code>~</code>, <code>&lt;&lt;</code>, <code>&gt;&gt;</code>.</li>
            <li>Comparisons: <code>==</code>, <code>!=</code>, <code>&lt;</code>, <code>&gt;</code>, <code>&lt;=</code>, <code>&gt;=</code>.</li>
            <li>Textual aliases: <code>NOT</code>, <code>AND</code>, <code>OR</code>, <code>XOR</code>.</li>
        </ul>
        <h2>Textual alias rules</h2>
        <ul>
            <li>Use spaces or parentheses to make textual operators explicit: <code>A AND B</code>, <code>NOT 1</code>, <code>NOT(1)</code>, <code>(A)OR(B)</code>.</li>
            <li>Names such as <code>AND_value</code>, <code>ORBIT</code>, <code>XOFFSET</code> and <code>NOT1</code> stay as identifiers.</li>
        </ul>
        <h2>Examples</h2>
        <h3>1. Basic arithmetic</h3>
        <pre>1 + 1
0x10 + 5
0b1010 * 3
(12 + 4) / 2</pre>
        <h3>2. Assignments and reuse</h3>
        <p><code>ANS</code> is updated with the last successful command result. You can use it like any other variable.</p>
        <pre>gp=0x89823A
gp >> 3
offset=0x1C
gp + offset
ANS + 4</pre>
        <h3>3. Bitwise workflows</h3>
        <pre>mask=0xFF
mask AND 0b10101010
flags=0b11001100
flags XOR mask
NOT 0x0F</pre>
        <h3>4. Comparisons and shifts</h3>
        <pre>value=0x20
(value & 0x0F) == 0
(value + 5) << 2</pre>
        <h2>Autocomplete</h2>
        <p>Variables saved in the current context appear as suggestions while typing identifiers.</p>
        <h2>Convert Toggle</h2>
        <p>When <b>Convert</b> is enabled, a successful non-negative integer result is sent to the Decimal converter input.</p>
        <h2>Workspace Windows</h2>
        <p><b>Variables</b> opens a table with the current assignments.</p>
        <p><b>Logs</b> opens a table with successful submitted commands in the form <code>expression =&gt; result</code>.</p>
        <p>Use the red minus button to remove a single variable or a single log line.</p>
    """,
)
