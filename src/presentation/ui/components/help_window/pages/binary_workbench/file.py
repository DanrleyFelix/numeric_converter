from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="File",
    subtitle="Opening files, scratch code, versions and internal files",
    html="""
        <p>The File menu controls the active source and the versioned edits attached to it.</p>
        <h2>Open File</h2>
        <ul>
            <li>Open binary files or assembly/code files in a tab.</li>
            <li>If the selected external file is already open, Binary Workbench moves to that tab instead of creating a duplicate.</li>
        </ul>
        <h2>New Scratch Code</h2>
        <ul>
            <li>Create a temporary assembly tab for quick tests, notes or small instruction experiments.</li>
            <li>Scratch tabs are not tied to an original binary until you save or copy their content elsewhere.</li>
        </ul>
        <h2>Version</h2>
        <ul>
            <li>Versions preserve named edit sets for the active tab.</li>
            <li>Create a version before saving a modified binary so the patch has a clear name.</li>
            <li><b>Att Version</b> updates the current active version with the current editor changes.</li>
            <li>Loaded versions can replace or restore instruction edits without rewriting the original source file.</li>
        </ul>
        <h2>Internal Files</h2>
        <ul>
            <li>Internal Files opens a mapped file inside the current binary, based on the configured LBA File System.</li>
            <li>Changes made in an internal file tab are mapped back to the parent binary offsets.</li>
            <li>This is useful when a disc image contains named files that you want to edit without manually calculating their file ranges.</li>
        </ul>
    """,
)
