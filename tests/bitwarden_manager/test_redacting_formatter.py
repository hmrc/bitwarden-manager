import logging

from _pytest.logging import LogCaptureFixture
from _pytest.monkeypatch import MonkeyPatch

from bitwarden_manager.redacting_formatter import get_bitwarden_logger, get_log_level


def test_get_bitwarden_logger(caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        logger = get_bitwarden_logger()

        # these are not real secrets
        logger.info("CLIENT_ID organization.KPL8P83fWXAvYvNYcbNWAKAcdNmn4Ssgne7w")
        logger.info("CLIENT_SECRET - 256STjxZJR2dVbspPY7TLb7CVKR7Wv ")
        logger.info("some other log line")

    assert "CLIENT_ID <REDACTED>" in caplog.text
    assert "KPL8P83fWXAvYvNYcbNWAKAcdNmn4Ssgne7w" not in caplog.text

    assert "CLIENT_SECRET - <REDACTED>" in caplog.text
    assert "256STjxZJR2dVbspPY7TLb7CVKR7Wv" not in caplog.text

    assert "some other log line" in caplog.text


def test_get_bitwarden_logger_override_with_env_var(monkeypatch: MonkeyPatch) -> None:
    assert get_bitwarden_logger().getEffectiveLevel() == logging.INFO

    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    assert get_bitwarden_logger().getEffectiveLevel() == logging.DEBUG


def test_get_log_level(monkeypatch: MonkeyPatch) -> None:
    assert get_log_level() == "INFO"

    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    assert get_log_level() == "DEBUG"