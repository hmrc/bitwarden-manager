import logging

from _pytest.logging import LogCaptureFixture

from bitwarden_manager.redacting_formatter import get_bitwarden_logger


def test_config_logging(caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        logger = get_bitwarden_logger()

        # these are not real secrets
        logger.info("CLIENT_ID organization.KPL8P83fWXAvYvNYcbNWAKAcdNmn4Ssgne7w")
        logger.info("CLIENT_SECRET - 256STjxZJR2dVbspPY7TLb7CVKR7Wv")

    assert "CLIENT_ID <REDACTED>" in caplog.text
    assert "CLIENT_SECRET - <REDACTED>" in caplog.text

    assert "KPL8P83fWXAvYvNYcbNWAKAcdNmn4Ssgne7w" not in caplog.text
    assert "256STjxZJR2dVbspPY7TLb7CVKR7Wv" not in caplog.text
