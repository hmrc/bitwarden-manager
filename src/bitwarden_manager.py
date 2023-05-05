import logging

from src.aws_secretsmanager_client import AwsSecretsManagerClient


class BitwardenManager():
    """docstring for BitwardenManager."""
    def __init__(self):
        self._logger = self._configure_logging("INFO")
        self._secretsmanager = AwsSecretsManagerClient()
        
    def run(self) -> None:
        self._logger.info(self.get_ldap_username())

    def get_ldap_username(self) -> str:
        return self._secretsmanager.get_secret_value('/bitwarden/ldap-username')

    def get_ldap_password(self) -> str:
        return self._secretsmanager.get_secret_value('/bitwarden/ldap-password')


    def _configure_logging(self, log_level: str) -> logging.Logger:
        logging.basicConfig(
            level=log_level,
            datefmt="%Y-%m-%dT%H:%M:%S",
            format="%(asctime)s %(levelname)s %(module)s %(message)s",
        )
        logging.getLogger().setLevel(log_level)
        logging.getLogger("botocore").setLevel(logging.ERROR)
        logging.getLogger("urllib3").setLevel(logging.ERROR)
        logging.getLogger("requests").setLevel(logging.ERROR)
        return logging.getLogger(self.__class__.__name__)
