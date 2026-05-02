class DONOR_TEXT:
    TITLE: str = "Donor"
    SUBTITLE: str = "Support the creator of Numeric WorkBench."
    PIX_LABEL: str = "PIX"
    BANK_LABEL: str = "Bank Account"
    PATREON_LABEL: str = "Patreon"
    LINKS_LABEL: str = "Links"
    OTHER_LABEL: str = "Other Options"
    PIX_KEY: str = "example.pix.key@numericworkbench.dev"
    BANK_ACCOUNT: str = "Bank 0001 · Branch 1234 · Account 56789-0"
    PATREON_URL: str = "https://www.patreon.com/example_creator"
    SUPPORT_LINKS: tuple[str, ...] = (
        "https://github.com/sponsors/example_creator",
        "https://ko-fi.com/example_creator",
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
