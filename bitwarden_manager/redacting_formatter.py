import logging
import re
from typing import List

PATTERNS = [r"organization.[\w-]{36}", r"\w{30}"]


class RedactingFormatter(logging.Filter):
    def __init__(self, patterns: List[str]) -> None:
        super().__init__()
        self._patterns = patterns

    def filter(self, record: logging.LogRecord) -> bool:
        for pattern in self._patterns:
            record.msg = re.sub(pattern, "<REDACTED>", record.msg)
        return True


def get_bitwarden_logger() -> logging.Logger:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.addFilter(RedactingFormatter(patterns=PATTERNS))

    return logger
