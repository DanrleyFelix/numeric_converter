from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="Internal Files",
    subtitle="Opening mapped files from a larger binary or disc image",
    html="""
        <p>Internal Files uses the configured LBA File System to expose a mapped file as its own tab.</p>
        <h2>LBA mapping</h2>
        <ul>
            <li>Configure the LBA File System before opening an internal file from a disc image.</li>
            <li>Each mapped entry provides the name, start location and length used to resolve the file range.</li>
            <li>The dialog prevents manual offset math when the same embedded file is edited repeatedly.</li>
        </ul>
        <h2>Opening a file</h2>
        <ul>
            <li>Choose an internal file from the list to open that range in a focused tab.</li>
            <li>If the mapped internal file is already open, Binary Workbench returns to the existing tab.</li>
            <li>The footer keeps the parent source visible so internal tabs remain distinguishable from normal files.</li>
        </ul>
        <h2>Saving changes</h2>
        <ul>
            <li>Edits made in an internal tab are mapped back to the parent binary offsets.</li>
            <li>Save the parent binary only after checking the internal tab changes are correct.</li>
        </ul>
    """,
)
