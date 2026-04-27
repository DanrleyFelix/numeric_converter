import re
from textwrap import dedent


HELP_SCROLLBAR_QSS = """
QScrollBar:vertical {
    background: rgba(15, 23, 38, 0.78);
    border: 1px solid rgba(36, 54, 83, 0.95);
    border-radius: 8px;
    width: 18px;
    margin: 8px 10px 8px 0px;
}
QScrollBar::handle:vertical {
    background: rgba(42, 88, 168, 0.92);
    border-radius: 10px;
    min-height: 34px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(62, 112, 201, 0.98);
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: rgba(15, 23, 38, 0.42);
    border-radius: 8px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::up-arrow:vertical,
QScrollBar::down-arrow:vertical {
    width: 0px;
    height: 0px;
    background: transparent;
    border: none;
}
"""


def render_help_html(title: str, subtitle: str, html: str) -> str:
    content_html = dedent(html).strip()
    content_html = re.sub(r">\s+<", "><", content_html)
    return f"""
    <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    padding: 14px 16px 14px 10px;
                    background-color: transparent;
                    color: #D8DDEF;
                    font-family: 'Segoe UI';
                    font-size: 14px;
                    line-height: 1.45;
                }}
                .page-shell {{ padding: 0; }}
                .page-header {{
                    margin-bottom: 12px;
                    padding-bottom: 8px;
                    border-bottom: 1px solid #243653;
                }}
                .page-title {{ color: #F3F6FF; font-size: 28px; font-weight: 600; }}
                .page-subtitle {{ color: #C8D2E8; font-size: 15px; line-height: 1.45; margin-top: 6px; }}
                h2, h3, p, li, pre {{ white-space: normal; }}
                h2 {{
                    color: #F1F4FF; font-size: 22px; font-weight: 600;
                    margin: 16px 0 8px 0; padding: 0 0 6px 0; border-bottom: 1px solid #243653;
                }}
                h3 {{
                    color: #ECF1FF; font-size: 17px; font-weight: 600;
                    margin: 12px 0 6px 0; padding: 0 0 4px 0; border-bottom: 1px solid #1B2A42;
                }}
                p {{ color: #D7DDED; margin: 0 0 8px 0; }}
                ul {{ color: #D7DDED; margin: 0 0 8px 0; padding: 0 0 0 18px; }}
                li {{ color: #D7DDED; margin: 3px 0; padding: 0; }}
                pre {{
                    color: #EEF3FF; margin: 0 0 8px 0; padding: 0;
                    white-space: pre-wrap; word-wrap: break-word; border: none; background: transparent;
                }}
                code {{ color: #F3F6FF; white-space: normal; background: transparent; }}
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
