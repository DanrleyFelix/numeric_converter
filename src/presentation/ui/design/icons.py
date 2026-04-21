import qtawesome as qta


class Icons:

    @staticmethod
    def numeric_workbench():
        return qta.icon("fa5s.project-diagram", color="#357A58")

    @staticmethod
    def calculator():
        return qta.icon("fa5s.calculator", color="#466cc3")

    @staticmethod
    def decimal():
        return qta.icon("fa5s.hashtag", color="#466cc3")

    @staticmethod
    def binary():
        return qta.icon("fa5s.code-branch", color="#466cc3")

    @staticmethod
    def hexadecimal():
        return qta.icon("fa5s.superscript", color="#466cc3")

    @staticmethod
    def command_window():
        return qta.icon("fa5s.terminal", color="#466cc3")

    @staticmethod
    def file():
        return qta.icon("fa5s.folder-open", color="#EAEAF5")

    @staticmethod
    def preferences():
        return qta.icon("fa5s.sliders-h", color="#EAEAF5")

    @staticmethod
    def help():
        return qta.icon("fa5s.book-open", color="#EAEAF5")
