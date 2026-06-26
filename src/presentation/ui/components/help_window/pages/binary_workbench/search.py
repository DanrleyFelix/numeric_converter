from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="Search",
    subtitle="Go to offsets, find data and select exact ranges",
    html="""
        <p>Search tools focus the current tab without changing the underlying data.</p>
        <h2>Go to</h2>
        <ul>
            <li>Navigate by File Offset, configured reference offsets, LBA, Label, Equate, Variable or named Internal File.</li>
            <li>When a target resolves to more than one offset, choose the desired result from the list.</li>
            <li>Labels and symbols are useful here because they let you navigate by meaning instead of memorized hex offsets.</li>
        </ul>
        <h2>Find</h2>
        <ul>
            <li>Search assembly instruction text, hex bytes or decoded text.</li>
            <li>Results can be activated directly to navigate to that offset.</li>
            <li>After a search, Start Offset is auto-filled with the end of the searched range so the next search can continue forward.</li>
            <li><b>Length</b> is in KB and is capped at <code>50KB</code> to keep searches responsive.</li>
        </ul>
        <h2>Select Block</h2>
        <ul>
            <li>Select an exact byte range by start/end or start/length.</li>
            <li>This is useful before copying data, comparing ranges or applying a focused edit.</li>
        </ul>
    """,
)
