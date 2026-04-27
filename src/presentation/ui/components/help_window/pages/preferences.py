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
        </ul>
        <h2>Toolbar option</h2>
        <ul>
            <li><b>Show Key Panel</b> stays in the Preferences menu on the toolbar.</li>
        </ul>
        <h2>Example configuration</h2>
        <pre>Decimal: group size 3, zero pad off
Binary: group size 8, zero pad on
Hex (BE): group size 2, zero pad off
Hex (LE): group size 4, zero pad on</pre>
    """,
)
