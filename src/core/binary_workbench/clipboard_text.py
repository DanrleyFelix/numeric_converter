"""Framework-independent clipboard text normalization for editor columns."""


def normalized_clipboard_text(text: str) -> str:
    """Normalize paragraph and platform line separators to newline characters."""

    return text.replace("\u2029", "\n").replace("\r\n", "\n").replace("\r", "\n")


def nonempty_clipboard_lines(text: str) -> list[str]:
    """Return clipboard lines that contain at least one visible character."""

    return [line for line in normalized_clipboard_text(text).split("\n") if line.strip()]


def without_empty_lines(text: str) -> str:
    """Remove empty clipboard lines while preserving non-empty line content."""

    return "\n".join(nonempty_clipboard_lines(text))
