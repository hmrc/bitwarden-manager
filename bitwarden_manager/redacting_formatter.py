import logging
import re
from os import environ
from typing import List

PATTERNS = [r"organization.[\w-]{36}", r"\b\w{30}\b"]


class RedactingFormatter(logging.Filter):
    def __init__(self, patterns: List[str]) -> None:
        super().__init__()
        RedactingFormatter.validate_patterns(patterns)
        self._patterns = patterns

    @staticmethod
    def validate_patterns(patterns_list: List[str]) -> None:
        for pattern in patterns_list:
            if not isinstance(pattern, str):
                raise ValueError("Patterns must be of type string")
            elif pattern == "":
                raise ValueError("Empty string as a pattern is not allowed as this will match and redact all log lines")

    def filter(self, record: logging.LogRecord) -> bool:
        for pattern in self._patterns:
            record.msg = re.sub(pattern, "<REDACTED>", record.msg)
        return True


def get_bitwarden_logger(extra_redaction_patterns: List[str]) -> logging.Logger:
    logger = logging.getLogger(__name__)
    logger.setLevel(get_log_level())
    redact_patterns = PATTERNS.copy()
    redact_patterns.extend(extra_redaction_patterns)
    logger.addFilter(RedactingFormatter(patterns=redact_patterns))

    return logger


def get_log_level() -> str:
    return environ.get("LOG_LEVEL", "INFO").upper()
