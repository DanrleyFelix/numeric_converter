class DONOR_TEXT:
    TITLE: str = "Donor"
    SUBTITLE: str = "Support the creator of Numeric and Binary WorkBench."
    PIX_LABEL: str = "PIX (Brazilian instant payment system)"
    BANK_LABEL: str = "Bank Account"
    PATREON_LABEL: str = "Patreon"
    LINKS_LABEL: str = "Links"
    OTHER_LABEL: str = "Other Options"
    PIX_KEY: str = "danrleyfelix@gmail.com"
    BANK_ACCOUNT: str = "Bank 104 · Branch 3880 · Account 932845322-0"
    PATREON_URL: str = "https://www.patreon.com/c/DanrleyFelix"
    SUPPORT_LINKS: tuple[str, ...] = (
        "https://github.com/DanrleyFelix/numeric_converter",
    )
    OTHER_SUPPORT_OPTIONS: tuple[str, ...] = (
        "Buy me a coffee",
        "Direct bank transfer",
    )


class DONOR_LAYOUT:
    WINDOW_WIDTH: int = 760
    WINDOW_HEIGHT: int = 460
    ROOT_LEFT: int = 28
    ROOT_TOP: int = 28
    ROOT_RIGHT: int = 28
    ROOT_BOTTOM: int = 28
    ROOT_SPACING: int = 12
    CARD_SPACING: int = 4
