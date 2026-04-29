from __future__ import annotations

from src.application.dto.command_render_result import CommandRenderResultDTO
from src.modules.utils import COLOR


def render_live_feedback(text: str, is_valid: bool) -> CommandRenderResultDTO:
    color = COLOR.SUCCESS if is_valid else COLOR.INCOMPLETE
    return CommandRenderResultDTO(lines=[text], color=color)


def render_submission_success(formatted: str) -> CommandRenderResultDTO:
    return CommandRenderResultDTO(
        lines=[formatted, ""],
        color=COLOR.SUCCESS,
        message=formatted,
    )


def render_submission_failure(active_line: str, message: str) -> CommandRenderResultDTO:
    return CommandRenderResultDTO(
        lines=[active_line, message],
        color=COLOR.FAILED,
        message=message,
    )


def render_invalid_expression(active_line: str) -> CommandRenderResultDTO:
    return CommandRenderResultDTO(
        lines=[active_line],
        color=COLOR.FAILED,
        message="Invalid expression.",
    )


def render_unknown_variable(text: str, is_incomplete: bool, message: str) -> CommandRenderResultDTO:
    if is_incomplete:
        return CommandRenderResultDTO(lines=[text], color=COLOR.INCOMPLETE)
    return CommandRenderResultDTO(lines=[text], color=COLOR.FAILED, message=message)


def render_invalid_input(
    corrected: str,
    original: str,
    pasted: bool,
    message: str,
) -> CommandRenderResultDTO:
    return CommandRenderResultDTO(
        lines=[corrected],
        color=COLOR.INCOMPLETE,
        message=None if corrected != original or pasted else message,
    )
