from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="Preferences",
    subtitle="Formatting, reference offsets, edit rules and performance options",
    html="""
        <p>Preferences adjust how the active editor behaves without changing the source file by themselves.</p>
        <h2>Bytes Formatter</h2>
        <ul>
            <li>Controls byte grouping and automatic uppercase formatting for bytes and instructions.</li>
            <li>Use it to keep byte edits easy to scan and consistent across rows.</li>
        </ul>
        <h2>Reference Offsets</h2>
        <ul>
            <li>Add extra offset columns beside File Offset.</li>
            <li>A common use is mapping file offsets to the real memory address used by a PSX emulator.</li>
            <li>This makes it easier to answer questions like where a certain instruction is located in RAM.</li>
        </ul>
        <h2>View</h2>
        <ul>
            <li>Choose which editor surfaces and offset columns stay visible in the active tab.</li>
            <li>Use View when you need a focused layout for bytes, assembly, raw instructions or reference offsets.</li>
            <li>The setting changes presentation only; it does not rewrite file data or version edits.</li>
        </ul>
        <h2>Rules</h2>
        <ul>
            <li>Rules control whether the Bytes or Assembly editor can be edited.</li>
            <li>They also control byte shifting and whether free editing is allowed after the original file end.</li>
            <li>Use stricter rules when you want patches to stay inside existing row boundaries.</li>
        </ul>
        <h2>Advanced Configuration</h2>
        <ul>
            <li>Choose CPU Arch and read mode for the active context.</li>
            <li>Block Size and Cache Max Blocks tune how much binary data the editor reads and keeps ready.</li>
            <li>Increasing cache can make Editor Assembly navigation smoother on large binaries, while smaller values reduce memory use.</li>
            <li>Selection Limit controls the maximum block size selected by Select Block and virtual selections.</li>
        </ul>
    """,
)
