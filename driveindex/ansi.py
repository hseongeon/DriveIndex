RESET = "\033[0m"

# Standard 16 ANSI colors
BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

# Bright colors
BRIGHT_BLACK = "\033[90m"
BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_WHITE = "\033[97m"


# 256-color support (foreground)
def color256(code: int) -> str:
    return f"\033[38;5;{code}m"


# Shades of gray (232~255)
GRAY_10 = color256(232)  # Very dark gray
GRAY_20 = color256(235)
GRAY_30 = color256(240)
GRAY_40 = color256(245)
GRAY_50 = color256(250)  # Light gray
GRAY_60 = color256(254)  # Almost white


def colorize(text: str, color: str) -> str:
    return f"{color}{text}{RESET}"
