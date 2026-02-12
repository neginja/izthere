import logging
import os
import sys
from datetime import datetime
from typing import Final, override

_LOG_LEVEL_MAP: Final[dict[str, int]] = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
    "notset": logging.NOTSET,
}


def _resolve_log_level(env_value: str | None) -> int:
    if not env_value:
        return logging.INFO

    normalized = env_value.strip().lower()
    return _LOG_LEVEL_MAP.get(normalized, logging.INFO)


class SimpleFormatter(logging.Formatter):
    fmt_str: Final = "%(asctime)s | %(levelname)-8s | %(message)s"
    date_fmt: Final = "%Y-%m-%d %H:%M:%S"

    def __init__(self):
        super().__init__(fmt=self.fmt_str, datefmt=self.date_fmt)

    @override
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        dfmt = datefmt or self.date_fmt
        dt = datetime.fromtimestamp(record.created)
        s = dt.strftime(dfmt)
        return f"{s},{int(record.msecs):03d}"

    @override
    def format(self, record: logging.LogRecord) -> str:
        return super().format(record)


def get_logger(name: str = "izthere") -> logging.Logger:
    """
    Returns a module-level logger that prints to stdout.
    The configuration is applied only once (the first call).
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # pseudo singleton

    env_level = os.getenv("LOG_LEVEL", "INFO")
    chosen_level = _resolve_log_level(env_level)

    logger.setLevel(chosen_level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(chosen_level)
    handler.setFormatter(SimpleFormatter())

    logger.addHandler(handler)
    logger.propagate = False  # avoid duplicate prints from root logger
    return logger
