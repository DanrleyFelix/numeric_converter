from __future__ import annotations

COMMENT_MARKERS = (";", "//", "#")


def comment_start(text: str) -> int:
    positions = [
        position
        for marker in COMMENT_MARKERS
        if (position := text.find(marker)) >= 0
    ]
    return min(positions) if positions else -1


def split_comment(text: str) -> tuple[str, str, str]:
    index = comment_start(text)
    if index < 0:
        return text, "", ""
    marker = next(
        marker
        for marker in COMMENT_MARKERS
        if text.startswith(marker, index)
    )
    return text[:index], marker, text[index + len(marker):]


def strip_comment(text: str) -> str:
    return split_comment(text)[0]