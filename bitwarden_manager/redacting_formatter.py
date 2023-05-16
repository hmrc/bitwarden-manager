import logging
import re
from os import environ
from typing import List

PATTERNS = [r"organization.[\w-]{36}", r"\b\w{30}\b"]


class RedactingFormatter(logging.Filter):
    def __init__(self, patterns: List[str]) -> None:
        super().__init__()
        self._patterns = patterns

    def filter(self, record: logging.LogRecord) -> bool:
        for pattern in self._patterns:
            record.msg = re.sub(pattern, "<REDACTED>", record.msg)
        return True


def get_bitwarden_logger() -> logging.Logger:
    logger = logging.getLogger(__name__)
    logger.setLevel(get_log_level())
    logger.addFilter(RedactingFormatter(patterns=PATTERNS))

    return logger


def get_log_level() -> str:
    return environ.get("LOG_LEVEL", "INFO").upper()
