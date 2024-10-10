import json
import subprocess  # nosec B404
import os
import base64

from logging import Logger
from tempfile import gettempdir
from typing import Dict, List, Optional, Any

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi

BW_SERVER_URI = "https://vault.bitwarden.eu"


class BitwardenVaultClientError(Exception):
    pass


class BitwardenVaultClientLoginError(Exception):
    pass


class BitwardenVaultClientIncorrectCredentialsError(Exception):
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
        cli_timeout: float,
    ) -> None:
        self.__logger = logger
        self.__client_secret = client_secret
        self.__client_id = client_id
        self.__password = password
        self.__export_enc_password = export_enc_password
        self.__session_token = None
        self.organisation_id = organisation_id
        self.cli_executable_path = cli_executable_path
        self.cli_timeout = cli_timeout

    def configure_server(self) -> None:
        self.__logger.info("Attempting to configure vault server")

        try:
            tmp_env = os.environ.copy()
            tmp_env["BITWARDENCLI_APPDATA_DIR"] = self.__get_config_dir()
            subprocess.check_call(
                [self.cli_executable_path, "config", "server", BW_SERVER_URI],
                env=tmp_env,
                shell=False,
                timeout=self.cli_timeout,
                text=True,
            )  # nosec B603

            self.__logger.info(f"Successfully set vault server to {BW_SERVER_URI}")
        except subprocess.CalledProcessError as e:
            raise BitwardenVaultClientError(f"Configuring server failed: {e}")

    def login(self) -> str:
        self.__logger.info("Attempting login")

        tmp_env = os.environ.copy()
        tmp_env["BITWARDENCLI_APPDATA_DIR"] = self.__get_config_dir()
        tmp_env["BW_CLIENTID"] = self.__client_id
        tmp_env["BW_CLIENTSECRET"] = self.__client_secret
        try:
            self.__logger.info("Logging in")

            output = subprocess.check_output(
                [self.cli_executable_path, "login", "--apikey"],
                env=tmp_env,
                shell=False,
                stderr=subprocess.PIPE,
                timeout=self.cli_timeout,
                text=True,
            )  # nosec B603

            self.__logger.info("Successfully logged in")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            self.__logger.error(f"Login failed due to: {e.stderr!r}")
            if e.stderr and "client_id or client_secret is incorrect" in e.stderr:
                raise BitwardenVaultClientIncorrectCredentialsError(e)
            else:
                raise BitwardenVaultClientLoginError(e)

        return output

    def _unlock(self) -> str:
        self.__logger.info("Attempting vault unlock")

        tmp_env = os.environ.copy()
        tmp_env["BITWARDENCLI_APPDATA_DIR"] = self.__get_config_dir()
        tmp_env["BW_PASSWORD"] = self.__password
        try:
            self.__logger.info("Unlocking vault")

            output = subprocess.check_output(
                [
                    self.cli_executable_path,
                    "unlock",
                    "--passwordenv",
                    "BW_PASSWORD",
                ],
                encoding="utf-8",
                env=tmp_env,
                shell=False,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.cli_timeout,
            )  # nosec B603
            session_token = output.split()[-1]

            self.__logger.info("Vault unlocked")

            return session_token
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            raise BitwardenVaultClientError(e)

    def logout(self) -> None:
        self.__logger.info("Attempting logout")

        if self.__session_token:
            try:
                self.__logger.info("Session found, logging out")
                tmp_env = os.environ.copy()
                tmp_env["BITWARDENCLI_APPDATA_DIR"] = self.__get_config_dir()
                output = subprocess.check_output(
                    [self.cli_executable_path, "logout"],
                    env=tmp_env,
                    encoding="utf-8",
                    shell=False,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=self.cli_timeout,
                )  # nosec B603

                self.__session_token = None
                self.__logger.debug(output)

                self.__logger.info("Successfully logged out")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                raise BitwardenVaultClientError(e)
        else:
            self.__logger.warning("No session found, skipping logout")

    def session_token(self) -> str:
        if not self.__session_token:
            self.authenticate()
        return self.__session_token  # type: ignore

    def authenticate(self) -> None:
        self.configure_server()
        self.login()
        self.__session_token = self._unlock()

    def export_vault(self, file_path: str) -> str:
        self.__logger.info("Attempting vault export")

        tmp_env = os.environ.copy()
        tmp_env["BITWARDENCLI_APPDATA_DIR"] = self.__get_config_dir()
        tmp_env["BW_SESSION"] = self.session_token()
        try:
            self.__logger.info(f"Beginning vault export to {file_path}")

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
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            # do not raise the called process error unless you want the export password in the stacktrace
            # https://github.com/bitwarden/clients/issues/5835
            e.cmd = "Redacting stack trace information for export to avoid logging password"
            raise BitwardenVaultClientError(e)

        return file_path

    def create_collections(self, missing_collection_names: List[str]) -> None:
        for collection in missing_collection_names:
            collection_object = {
                "organizationId": self.organisation_id,
                "name": collection,
                "externalId": BitwardenPublicApi.external_id_base64_encoded(collection),
            }
            json_collection = json.dumps(collection_object).encode("utf-8")
            json_encoded = base64.b64encode(json_collection)
            tmp_env = os.environ.copy()
            tmp_env["BITWARDENCLI_APPDATA_DIR"] = self.__get_config_dir()
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
                    timeout=self.cli_timeout,
                    stdout=subprocess.DEVNULL,
                )  # nosec B603

                self.__logger.info(f"Created collection: {collection}")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                raise BitwardenVaultClientError(e)

    def list_unconfirmed_users(self) -> List[Dict[str, str]]:
        tmp_env = os.environ.copy()
        tmp_env["BITWARDENCLI_APPDATA_DIR"] = self.__get_config_dir()
        tmp_env["BW_SESSION"] = self.session_token()
        try:
            out = subprocess.check_output(
                [
                    self.cli_executable_path,
                    "list",
                    "org-members",
                    "--organizationid",
                    self.organisation_id,
                ],
                shell=False,
                env=tmp_env,
                text=True,
                encoding="utf-8",
                timeout=self.cli_timeout,
            )  # nosec B603
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            raise BitwardenVaultClientError(e)

        json_response = json.loads(out)
        unconfirmed_users = []
        for user in json_response:
            if user.get("status") == 1:
                unconfirmed_users.append(
                    {
                        "email": user.get("email"),
                        "id": user.get("id"),
                    }
                )
        return unconfirmed_users

    def confirm_user(self, user_id: str) -> Any:
        tmp_env = os.environ.copy()
        tmp_env["BITWARDENCLI_APPDATA_DIR"] = self.__get_config_dir()
        tmp_env["BW_SESSION"] = self.session_token()
        try:
            subprocess.check_call(
                [
                    self.cli_executable_path,
                    "confirm",
                    "org-member",
                    user_id,
                    "--organizationid",
                    self.organisation_id,
                ],
                shell=False,
                env=tmp_env,
                timeout=self.cli_timeout,
            )  # nosec B603
            self.__logger.debug(f"User {user_id} confirmed successfully")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            raise BitwardenVaultClientError(e)

    def __get_config_dir(self) -> str:
        return "/tmp/.config"
