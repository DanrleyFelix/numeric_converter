import re
from textwrap import dedent

from src.presentation.ui.components.help_window.constants import (
    HELP_HTML_FONT,
    HELP_HTML_MARGIN,
    HELP_HTML_SIZE,
    HELP_HTML_SPACING,
)
from src.presentation.ui.helpers.load_qss import THEME_TOKENS


def _token(name: str) -> str:
    return THEME_TOKENS[name]


def render_help_html(title: str, subtitle: str, html: str) -> str:
    content_html = dedent(html).strip()
    content_html = re.sub(r">\s+<", "><", content_html)
    return f"""
    <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    padding: {HELP_HTML_MARGIN.BODY_TOP}px {HELP_HTML_MARGIN.BODY_RIGHT}px {HELP_HTML_MARGIN.BODY_BOTTOM}px {HELP_HTML_MARGIN.BODY_LEFT}px;
                    background-color: transparent;
                    color: {_token("help-text-main")};
                    font-family: {_token(HELP_HTML_FONT.BODY)};
                    font-size: {HELP_HTML_SIZE.BODY}px;
                    line-height: {HELP_HTML_SPACING.LINE_HEIGHT};
                }}
                .page-shell {{ padding: 0; }}
                .page-header {{
                    margin-bottom: {HELP_HTML_SPACING.HEADER_BOTTOM}px;
                    padding-bottom: {HELP_HTML_SPACING.HEADER_PADDING_BOTTOM}px;
                    border-bottom: 1px solid {_token("help-border-strong")};
                }}
                .page-title {{ color: {_token("help-text-title")}; font-size: {HELP_HTML_SIZE.TITLE}px; font-weight: 600; }}
                .page-subtitle {{ color: {_token("help-text-subtitle")}; font-size: {HELP_HTML_SIZE.SUBTITLE}px; line-height: {HELP_HTML_SPACING.LINE_HEIGHT}; margin-top: {HELP_HTML_SPACING.SUBTITLE_TOP}px; }}
                h2, h3, p, li, pre {{ white-space: normal; }}
                h2 {{
                    color: {_token("help-text-heading")}; font-size: {HELP_HTML_SIZE.HEADING}px; font-weight: 600;
                    margin: {HELP_HTML_MARGIN.SECTION_TOP}px 0 {HELP_HTML_MARGIN.SECTION_BOTTOM}px 0; padding: 0 0 {HELP_HTML_SPACING.HEADING_BORDER_BOTTOM}px 0; border-bottom: 1px solid {_token("help-border-strong")};
                }}
                h3 {{
                    color: {_token("help-text-heading-soft")}; font-size: {HELP_HTML_SIZE.SUBHEADING}px; font-weight: 600;
                    margin: {HELP_HTML_MARGIN.SUBSECTION_TOP}px 0 {HELP_HTML_MARGIN.SUBSECTION_BOTTOM}px 0; padding: 0 0 {HELP_HTML_SPACING.SUBHEADING_BORDER_BOTTOM}px 0; border-bottom: 1px solid {_token("help-border-soft")};
                }}
                p {{ color: {_token("help-text-main")}; margin: 0 0 {HELP_HTML_SPACING.PARAGRAPH_BOTTOM}px 0; }}
                ul {{ color: {_token("help-text-main")}; margin: 0 0 {HELP_HTML_SPACING.LIST_BOTTOM}px 0; padding: 0 0 0 {HELP_HTML_SPACING.LIST_LEFT}px; }}
                li {{ color: {_token("help-text-main")}; margin: {HELP_HTML_SPACING.LIST_ITEM_VERTICAL}px 0; padding: 0; }}
                pre {{
                    color: {_token("help-text-code")}; margin: 0 0 {HELP_HTML_SPACING.PARAGRAPH_BOTTOM}px 0; padding: 0;
                    font-family: {_token(HELP_HTML_FONT.CODE)};
                    white-space: pre-wrap; word-wrap: break-word; border: none; background: transparent;
                }}
                code {{ color: {_token("help-text-title")}; white-space: normal; background: transparent; font-family: {_token(HELP_HTML_FONT.CODE)}; }}
            </style>
        </head>
        <body>
            <div class="page-shell">
                <div class="page-header">
                    <div class="page-title">{title}</div>
                    <div class="page-subtitle">{subtitle}</div>
                </div>
                {content_html}
            </div>
        </body>
    </html>
    """
