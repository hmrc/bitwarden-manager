import logging

import pytest
from _pytest.logging import LogCaptureFixture
from _pytest.monkeypatch import MonkeyPatch

from bitwarden_manager.redacting_formatter import get_bitwarden_logger, get_log_level


def test_get_bitwarden_logger(caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        logger = get_bitwarden_logger(extra_redaction_patterns=[])

        # these are not real secrets
        logger.info("CLIENT_ID organization.KPL8P83fWXAvYvNYcbNWAKAcdNmn4Ssgne7w")
        logger.info("CLIENT_SECRET - 256STjxZJR2dVbspPY7TLb7CVKR7Wv ")
        logger.info("some other log line")

    assert "CLIENT_ID <REDACTED>" in caplog.text
    assert "KPL8P83fWXAvYvNYcbNWAKAcdNmn4Ssgne7w" not in caplog.text

    assert "CLIENT_SECRET - <REDACTED>" in caplog.text
    assert "256STjxZJR2dVbspPY7TLb7CVKR7Wv" not in caplog.text

    assert "some other log line" in caplog.text


def test_get_bitwarden_logger_extra_patterns(caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        logger = get_bitwarden_logger(extra_redaction_patterns=["remove me"])

        # these are not real secrets
        logger.info("some other log line")
        logger.info("something else remove me")

    assert "something else <REDACTED>" in caplog.text
    assert "remove me" not in caplog.text

    assert "some other log line" in caplog.text


def test_get_bitwarden_logger_empty_string_should_error(caplog: LogCaptureFixture) -> None:
    with pytest.raises(
        ValueError, match="Empty string as a pattern is not allowed as this will match and redact all log lines"
    ):
        get_bitwarden_logger(extra_redaction_patterns=[""])


def test_get_redacting_formater_errors_on_non_string_input(caplog: LogCaptureFixture) -> None:
    with pytest.raises(ValueError, match="Patterns must be of type string"):
        get_bitwarden_logger(extra_redaction_patterns=[12])  # type: ignore

    get_bitwarden_logger(extra_redaction_patterns=[r"organization.[\w-]{36}"])

    class TestStringClass(str):
        pass

    get_bitwarden_logger(extra_redaction_patterns=[TestStringClass("foo")])


def test_get_bitwarden_logger_override_with_env_var(monkeypatch: MonkeyPatch) -> None:
    assert get_bitwarden_logger(extra_redaction_patterns=[]).getEffectiveLevel() == logging.INFO

    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    assert get_bitwarden_logger(extra_redaction_patterns=[]).getEffectiveLevel() == logging.DEBUG


def test_get_log_level(monkeypatch: MonkeyPatch) -> None:
    assert get_log_level() == "INFO"

    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    assert get_log_level() == "DEBUG"
