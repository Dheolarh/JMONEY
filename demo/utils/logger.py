import sys

class Logger:
    """A simple, clean logger for terminal output."""

    _BLUE = '\033[94m'
    _GREEN = '\033[92m'
    _YELLOW = '\033[93m'
    _RED = '\033[91m'
    _ENDC = '\033[0m'
    _BOLD = '\033[1m'

    @staticmethod
    def _log(color, symbol, message):
        sys.stdout.write(f"{color}{symbol} {message}{Logger._ENDC}\n")
        sys.stdout.flush()

    @staticmethod
    def start_section(title):
        sys.stdout.write(f"\n{Logger._BOLD}{Logger._BLUE}## {title.upper()} ##{Logger._ENDC}\n")
        sys.stdout.flush()

    @staticmethod
    def log(message, indent=1):
        prefix = "  " * indent
        sys.stdout.write(f"{prefix}- {message}\n")
        sys.stdout.flush()

    @staticmethod
    def info(message, indent=2):
        prefix = "  " * indent
        sys.stdout.write(f"{Logger._YELLOW}{prefix}ℹ {message}{Logger._ENDC}\n")
        sys.stdout.flush()

    @staticmethod
    def success(message, indent=1):
        prefix = "  " * indent
        Logger._log(Logger._GREEN, f"{prefix}✅", message)

    @staticmethod
    def fail(message, indent=1):
        prefix = "  " * indent
        Logger._log(Logger._RED, f"{prefix}❌", message)


logger = Logger()