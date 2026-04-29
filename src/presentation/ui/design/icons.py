import qtawesome as qta

from src.presentation.ui.helpers.load_qss import THEME_TOKENS


class Icons:

    @staticmethod
    def _icon(name: str, token_name: str, **kwargs):
        return qta.icon(name, color=THEME_TOKENS[token_name], **kwargs)

    @staticmethod
    def numeric_workbench():
        return Icons._icon("fa5s.project-diagram", "icon-brand")

    @staticmethod
    def calculator():
        return Icons._icon("fa5s.calculator", "icon-primary")

    @staticmethod
    def decimal():
        return Icons._icon("fa5s.hashtag", "icon-primary")

    @staticmethod
    def binary():
        return Icons._icon("fa5s.code-branch", "icon-primary")

    @staticmethod
    def hexadecimal():
        return Icons._icon("fa5s.superscript", "icon-primary")

    @staticmethod
    def command_window():
        return Icons._icon("fa5s.terminal", "icon-primary")

    @staticmethod
    def file():
        return Icons._icon("fa5s.folder-open", "icon-toolbar")

    @staticmethod
    def preferences():
        return Icons._icon("fa5s.cog", "icon-toolbar")

    @staticmethod
    def help():
        return Icons._icon("fa5s.book-open", "icon-toolbar")

    @staticmethod
    def copy():
        return Icons._icon("fa5s.copy", "icon-toolbar")

    @staticmethod
    def remove():
        return Icons._icon(
            "fa5s.trash-alt",
            "icon-toolbar",
            color_active=THEME_TOKENS["icon-danger"],
            color_selected=THEME_TOKENS["icon-danger"],
        )

    @staticmethod
    def remove_hover():
        return Icons._icon("fa5s.trash-alt", "icon-danger")
