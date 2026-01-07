from .theme import ColorPalette
from .metrics import Metrics
from .typography import Typography


class StyleSheetBuilder:

    @staticmethod
    def build() -> str:
        return f"""
        QWidget {{
            background-color: {ColorPalette.BACKGROUND};
            color: {ColorPalette.TEXT_PRIMARY};
            font-family: {Typography.FONT_FAMILY};
            font-size: {Typography.CONTENT}px;
        }}

        QLabel#Title {{
            font-size: {Typography.TITLE}px;
            font-weight: 600;
        }}

        QLabel#Subtitle {{
            font-size: {Typography.SUBTITLE}px;
            color: {ColorPalette.TEXT_SECONDARY};
        }}

        QLineEdit {{
            background-color: {ColorPalette.SURFACE};
            border: 1px solid {ColorPalette.BORDER};
            border-radius: {Metrics.RADIUS_SM}px;
            padding: {Metrics.PADDING_MD}px;
        }}

        QWidget#Card {{
            background-color: {ColorPalette.SURFACE};
            border: 1px solid {ColorPalette.BORDER};
            border-radius: {Metrics.RADIUS_MD}px;
            padding: {Metrics.PADDING_LG}px;
        }}
        """
