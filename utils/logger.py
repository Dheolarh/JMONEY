import sys
import threading
import time
import json


class Logger:
    """A simple, clean logger for terminal output with lightweight metrics support."""

    _BLUE = '\033[94m'
    _GREEN = '\033[92m'
    _YELLOW = '\033[93m'
    _RED = '\033[91m'
    _ENDC = '\033[0m'
    _BOLD = '\033[1m'

    def __init__(self):
        # simple in-memory metrics registry: {metric_name: int}
        self._metrics = {}
        self._lock = threading.Lock()

    def _log(self, color, symbol, message):
        sys.stdout.write(f"{color}{symbol} {message}{Logger._ENDC}\n")
        sys.stdout.flush()

    def start_section(self, title):
        sys.stdout.write(f"\n{Logger._BOLD}{Logger._BLUE}## {title.upper()} ##{Logger._ENDC}\n")
        sys.stdout.flush()

    def log(self, message, indent=1):
        prefix = "  " * indent
        sys.stdout.write(f"{prefix}- {message}\n")
        sys.stdout.flush()

    def info(self, message, indent=2):
        prefix = "  " * indent
        sys.stdout.write(f"{Logger._YELLOW}{prefix}ℹ {message}{Logger._ENDC}\n")
        sys.stdout.flush()

    def success(self, message, indent=1):
        prefix = "  " * indent
        self._log(Logger._GREEN, f"{prefix}✅", message)

    def fail(self, message, indent=1):
        prefix = "  " * indent
        self._log(Logger._RED, f"{prefix}❌", message)

    # Structured logging helper that prints a JSON line with timestamp
    def structured(self, event: str, **fields):
        payload = {
            'ts': time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime()),
            'event': event,
            **fields
        }
        sys.stdout.write(json.dumps(payload, default=str) + "\n")
        sys.stdout.flush()

    # Lightweight metric incrementer
    def increment_metric(self, name: str, value: int = 1):
        with self._lock:
            self._metrics[name] = self._metrics.get(name, 0) + int(value)

    def get_metrics(self) -> dict:
        with self._lock:
            return dict(self._metrics)


logger = Logger()
