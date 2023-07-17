import json
import subprocess  # nosec B404
import os
import base64
from logging import Logger
from typing import Optional

BITWARDEN_CLIENT_TIMEOUT = 15


class BitwardenVaultClientError(Exception):
    pass


class BitwardenVaultClient:
    __session_token: Optional[str]

    def __init__(
        self,
        logger: Logger,
        client_id: str,
        client_secret: str,
        password: str,
        export_enc_password: str,
        cli_executable_path: str,
        organisation_id: str,
    ) -> None:
        self.__logger = logger
        self.__client_secret = client_secret
        self.__client_id = client_id
        self.__password = password
        self.__export_enc_password = export_enc_password
        self.__session_token = None
        self.organisation_id = organisation_id
        self.cli_executable_path = cli_executable_path

    def login(self) -> str:
        tmp_env = os.environ.copy()
        tmp_env["BW_CLIENTID"] = self.__client_id
        tmp_env["BW_CLIENTSECRET"] = self.__client_secret
        try:
            output = subprocess.check_output(
                [self.cli_executable_path, "login", "--apikey"],
                env=tmp_env,
                shell=False,
                timeout=BITWARDEN_CLIENT_TIMEOUT,
                text=True,
            )  # nosec B603
        except subprocess.CalledProcessError as e:
            raise BitwardenVaultClientError(e)
        return output

    def _unlock(self) -> str:
        tmp_env = os.environ.copy()
        tmp_env["BW_PASSWORD"] = self.__password
        try:
            output = subprocess.check_output(
                [
                    self.cli_executable_path,
                    "unlock",
                    "--passwordenv",
                    "BW_PASSWORD",
                ],
                shell=False,
                env=tmp_env,
                text=True,
                encoding="utf-8",
                timeout=BITWARDEN_CLIENT_TIMEOUT,
            )  # nosec B603
            session_token = output.split()[-1]
            return session_token
        except subprocess.CalledProcessError as e:
            raise BitwardenVaultClientError(e)

    def logout(self) -> None:
        if self.__session_token:
            try:
                output = subprocess.check_output(
                    [self.cli_executable_path, "logout"],
                    shell=False,
                    text=True,
                    encoding="utf-8",
                    timeout=BITWARDEN_CLIENT_TIMEOUT,
                )  # nosec B603
                self.__session_token = None
                self.__logger.debug(output)
            except subprocess.CalledProcessError as e:
                raise BitwardenVaultClientError(e)
        else:
            self.__logger.warning("Not logged in so ignoring call to logout")

    def session_token(self) -> str:
        if not self.__session_token:
            self.authenticate()
        return self.__session_token  # type: ignore

    def authenticate(self) -> None:
        self.login()
        self.__session_token = self._unlock()

    def export_vault(self, file_path: str) -> str:
        tmp_env = os.environ.copy()
        tmp_env["BW_SESSION"] = self.session_token()
        try:
            subprocess.check_call(
                [
                    self.cli_executable_path,
                    "export",
                    "--format",
                    "encrypted_json",
                    "--password",
                    self.__export_enc_password,
                    "--output",
                    file_path,
                    "--organizationid",
                    self.organisation_id,
                ],
                env=tmp_env,
                stdout=subprocess.PIPE,
                shell=False,
            )  # nosec B603
            self.__logger.info(f"Exported vault backup to {file_path}")
        except subprocess.CalledProcessError as e:
            # do not raise the called process error unless you want the export password in the stacktrace
            # https://github.com/bitwarden/clients/issues/5835
            e.cmd = "Redacting stack trace information for export to avoid logging password"
            raise BitwardenVaultClientError(e)

        return file_path

    def create_collection(self, teams: list[str], existing_collections: dict[str, str]) -> None:
        missing_collection = [team for team in teams if not existing_collections.get(team)]
        if not missing_collection:
            self.__logger.info("No missing collections found")
            return

        for collection in missing_collection:
            collection_object = {
                "organizationId": self.organisation_id,
                "name": collection,
                "externalId": collection,
            }
            json_collection = json.dumps(collection_object).encode("utf-8")
            json_encoded = base64.b64encode(json_collection)
            tmp_env = os.environ.copy()
            tmp_env["BW_SESSION"] = self.session_token()
            try:
                subprocess.check_call(
                    [
                        self.cli_executable_path,
                        "create",
                        "org-collection",
                        "--organizationid",
                        self.organisation_id,
                        json_encoded,
                    ],
                    env=tmp_env,
                    shell=False,
                    timeout=BITWARDEN_CLIENT_TIMEOUT,
                )  # nosec B603
                self.__logger.info(f"Created {collection} successfully")
            except subprocess.CalledProcessError as e:
                raise BitwardenVaultClientError(e)
