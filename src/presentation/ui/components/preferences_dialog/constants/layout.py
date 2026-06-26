class PREFERENCES_DIALOG_SIZE:
    WIDTH: int = 520
    HEIGHT: int = 460
    ACTION_BUTTON_WIDTH: int = 160
    ACTION_BUTTON_HEIGHT: int = 38
    GROUP_SIZE_WIDTH: int = 86


PREFERENCES_GROUP_SIZE_VALUES: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6, 7, 8, 16,)


class LOG_PREFERENCES_SIZE:
    WIDTH: int = 620
    HEIGHT: int = 420
    ACTION_BUTTON_WIDTH: int = 160
    ACTION_BUTTON_HEIGHT: int = 38


class PREFERENCES_DIALOG_MARGIN:
    ROOT_LEFT: int = 20
    ROOT_TOP: int = 20
    ROOT_RIGHT: int = 20
    ROOT_BOTTOM: int = 20
    BUTTONS_LEFT: int = 0
    BUTTONS_TOP: int = 12
    BUTTONS_RIGHT: int = 0
    BUTTONS_BOTTOM: int = 0


class LOG_PREFERENCES_MARGIN:
    ROOT_LEFT: int = 20
    ROOT_TOP: int = 20
    ROOT_RIGHT: int = 20
    ROOT_BOTTOM: int = 20
    BUTTONS_LEFT: int = 0
    BUTTONS_TOP: int = 12
    BUTTONS_RIGHT: int = 0
    BUTTONS_BOTTOM: int = 0


class PREFERENCES_DIALOG_SPACING:
    ROOT: int = 18
    BUTTONS: int = 12
    GRID_HORIZONTAL: int = 28
    GRID_LAYOUT: int = 0
    GRID_HEADER: int = 20
    GRID_IDENTICAL_ROWS: int = 15
    GRID_HEADER_ROW: int = 0
    GRID_HEADER_SPACER_ROW: int = 1
    GRID_FIRST_DATA_ROW: int = 2
    GRID_ROW_STEP: int = 2


class LOG_PREFERENCES_SPACING:
    ROOT: int = 18
    OPTIONS: int = 15
    BUTTONS: int = 12
