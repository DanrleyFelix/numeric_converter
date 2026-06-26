from src.presentation.ui.components.help_window.page import HelpPageDefinition


PAGE = HelpPageDefinition(
    title="Main Window",
    subtitle="Editor panes, offsets and tabs for binary or assembly work",
    html="""
        <p>Binary Workbench is built around tabs. Each tab owns its current file, source rows, symbols, versions and navigation state.</p>
        <h2>Editor areas</h2>
        <ul>
            <li><b>Editor Assembly</b>: the main assembly editing area. Labels, symbols and commands are meant to be typed here.</li>
            <li><b>Bytes</b>: the byte view for the same rows. It is useful when checking encoded instructions or editing raw values.</li>
            <li><b>Raw Instructions</b>: shows the preprocessed instruction text that the assembler receives.</li>
            <li><b>File Offset</b>: shows where the row lives in the opened file.</li>
        </ul>
        <h2>Tabs</h2>
        <ul>
            <li>Use tabs to keep several files or focused views open at once.</li>
            <li>Opening a file that is already open switches to its existing tab.</li>
            <li>Internal file tabs are marked in the footer so they are easy to distinguish from normal files.</li>
        </ul>
        <h2>Footer</h2>
        <ul>
            <li>The footer reports cursor offset, selected block and byte length.</li>
            <li><b>CPU Arch</b> shows the architecture used to assemble, disassemble and validate commands.</li>
            <li>Internal tabs also show the source file they came from.</li>
        </ul>
    """,
)
