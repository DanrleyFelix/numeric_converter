from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="Converter",
    subtitle="Working with Decimal, Binary, Hex (BE) and Hex (LE)",
    html="""
        <p>The converter keeps the typed content separate from the formatted display, so padding and grouping do not corrupt editing.</p>
        <h2>Inputs</h2>
        <ul>
            <li>Each field name appears as the field placeholder: <b>Decimal</b>, <b>Binary</b>, <b>Hex (BE)</b> and <b>Hex (LE)</b>.</li>
            <li><b>Decimal</b>: digits <code>0-9</code>.</li>
            <li><b>Binary</b>: digits <code>0</code> and <code>1</code>.</li>
            <li><b>Hex (BE)</b> and <b>Hex (LE)</b>: digits <code>0-9</code> and letters <code>A-F</code>.</li>
        </ul>
        <h2>Keyboard navigation</h2>
        <ul>
            <li>The cursor starts in <b>Decimal</b> when Numeric Workbench opens.</li>
            <li><code>Tab</code> moves through <b>Decimal</b>, <b>Binary</b>, <b>Hex (BE)</b>, <b>Hex (LE)</b>, <b>Command Window</b> and back to <b>Decimal</b>.</li>
            <li><code>F1</code> focuses Decimal, <code>F2</code> Binary, <code>F3</code> Hex (BE), <code>F4</code> Hex (LE) and <code>F5</code> Command Window.</li>
            <li><code>Tab</code> only navigates between edit fields; it does not insert tab spaces.</li>
        </ul>
        <h2>Padding and grouping</h2>
        <ul>
            <li><b>Group size</b> controls how many characters appear in each group.</li>
            <li><b>Zero pad</b> pads the effective input before conversion.</li>
            <li>Hex values with an odd number of digits receive one leading zero to complete a byte.</li>
            <li>Hex (LE) interprets the effective byte sequence as little-endian.</li>
        </ul>
        <h2>Copying values</h2>
        <ul>
            <li>Normal copy keeps the field exactly as displayed, including spaces.</li>
            <li>The small copy icon beside each field copies the same value without spaces.</li>
            <li><code>Alt+C</code> copies the raw value from the focused converter field.</li>
        </ul>
        <h2>Examples</h2>
        <pre>Decimal: 255
Binary: 11111111
Hex (BE): FF
Hex (LE): FF

Hex (LE), group size 4, zero pad enabled:
typed: 45    effective: 0045
typed: 454   effective: 0454</pre>
    """,
)
