from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="Preferences",
    subtitle="Converter formatting",
    html="""
        <p>Preferences configure converter display rules.</p>
        <h2>Converter options</h2>
        <ul>
            <li><b>Group size</b>: controls visual grouping for each converter field.</li>
            <li><b>Zero pad</b>: pads the effective value before formatting and conversion.</li>
            <li><code>Alt+P</code> opens Preferences &gt; Converter.</li>
        </ul>
        <h2>Toolbar option</h2>
        <ul>
            <li><b>Show Key Panel</b> stays in the Preferences menu on the toolbar.</li>
            <li><code>Alt+S</code> toggles Show Key Panel.</li>
            <li><code>Alt+X</code> toggles Auto Convert.</li>
        </ul>
        <h2>Logs</h2>
        <ul>
            <li><b>Logs</b> in the Preferences menu opens the fixed-size log configuration dialog.</li>
            <li><b>Enable logs</b> controls whether successful Command Window expressions are saved in the Logs table.</li>
            <li>The filters control assignment-only expressions, single unary expressions, expressions without operators and expressions containing assignment.</li>
            <li><b>Log only expressions with one or more binary operators</b> keeps Enable logs active and disables the other expression filters.</li>
            <li><code>Alt+L</code> opens Preferences &gt; Logs and also toggles Enable logs inside that dialog.</li>
        </ul>
        <h2>Example configuration</h2>
        <pre>Decimal: group size 3, zero pad off
Binary: group size 8, zero pad on
Hex (BE): group size 2, zero pad off
Hex (LE): group size 4, zero pad on</pre>
    """,
)
