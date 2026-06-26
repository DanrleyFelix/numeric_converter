from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="Versions",
    subtitle="Named edit sets for saving and restoring binary changes",
    html="""
        <p>Versions let the active tab keep patch sets separate from the original loaded file.</p>
        <h2>Create and update</h2>
        <ul>
            <li>Open <b>Version</b> before saving a modified binary when the current edits need a named record.</li>
            <li><b>Att Version</b> updates the active version with the current editor state.</li>
            <li>The version name should describe the patch or experiment, not the source file itself.</li>
        </ul>
        <h2>Load and replace</h2>
        <ul>
            <li>Loaded versions can restore instruction edits into the current tab.</li>
            <li>Replacing a loaded version changes the visible edited rows without rewriting the original file immediately.</li>
            <li>Save the file only after confirming the active version contains the intended edits.</li>
        </ul>
        <h2>Tab state</h2>
        <ul>
            <li>Each tab owns its version data and dirty state.</li>
            <li>Closing a tab with meaningful unsaved edits asks before discarding those changes.</li>
        </ul>
    """,
)
