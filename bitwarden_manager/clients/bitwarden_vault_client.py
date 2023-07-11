import boto3
import datetime
import json
import subprocess  # nosec B404
import os
from logging import Logger
import base64

from botocore.exceptions import BotoCoreError, ClientError
from typing import IO


class BitwardenVaultClient:
    def __init__(
        self,
        logger: Logger,
        client_id: str,
        client_secret: str,
        password: str,
        export_enc_password: str,
        cli_executable_path: str,
    ) -> None:
        self.__logger = logger
        self.__client_secret = client_secret
        self.__client_id = client_id
        self.__password = password
        self.__export_enc_password = export_enc_password
        self.__session_token = ""  # nosec B105
        self.organisation_id = os.environ["ORGANISATION_ID"]
        self.cli_executable_path = cli_executable_path

    def login(self) -> str:
        tmp_env = os.environ.copy()
        tmp_env["BW_CLIENTID"] = self.__client_id
        tmp_env["BW_CLIENTSECRET"] = self.__client_secret
        proc = subprocess.Popen(
            [self.cli_executable_path, "login", "--apikey"], env=tmp_env, shell=False, stdout=subprocess.PIPE
        )  # nosec B603
        (out, _err) = proc.communicate()
        self.__logger.info(f"Response {str(_err)}")
        if out:
            self.__logger.info("Logged in to Bitwarden Vault")
            return out.decode("utf-8")
        else:
            raise Exception("Failed to login")

    def unlock(self) -> str:
        proc = subprocess.Popen(
            [self.cli_executable_path, "unlock", self.__password], stdout=subprocess.PIPE, shell=False
        )  # nosec B603
        (out, _err) = proc.communicate()
        if out:
            string = out.decode("utf-8")
            self.__logger.info("Unlocked Bitwarden Vault")
            self.__session_token = string.split()[-1]
            return string
        else:
            raise Exception("Failed to unlock")

    def logout(self) -> str:
        proc = subprocess.Popen([self.cli_executable_path, "logout"], stdout=subprocess.PIPE, shell=False)  # nosec B603
        (out, _err) = proc.communicate()
        if out:
            return out.decode("utf-8")
        else:
            raise Exception("Failed to logout")

    def export_vault(self) -> str:
        if not self.__session_token:
            self.login()
            self.unlock()
        now = datetime.datetime.now()
        output_path = f"/tmp/bw_backup_{now}.json"  # nosec B108
        proc = subprocess.Popen(
            [
                self.cli_executable_path,
                "export",
                "--session",
                self.__session_token,
                "--format",
                "encrypted_json",
                "--password",
                self.__export_enc_password,
                "--output",
                output_path,
                "--organizationid",
                self.organisation_id,
            ],
            stdout=subprocess.PIPE,
            shell=False,
        )  # nosec B603
        (_out, _err) = proc.communicate()
        self.__logger.info(f"Exported vault backup to {output_path}")
        return output_path

    def write_file_to_s3(self, bucket_name: str, filepath: str) -> None:
        try:
            s3 = boto3.client("s3")
            s3.put_object(Bucket=bucket_name, Key=filepath, Body=self.file_from_path(filepath))
        except (BotoCoreError, ClientError) as e:
            raise Exception("Failed to write to S3", e) from e

    def file_from_path(self, filepath: str) -> IO[bytes]:
        return open(filepath, "rb")

    def create_collection(self, teams: list[str], existing_collections: dict[str, str]) -> None:
        missing_collection = [team for team in teams if not existing_collections.get(team)]
        if not missing_collection:
            self.__logger.info("No missing collections found")
            return

        if not self.__session_token:
            self.login()
            self.unlock()
        for collection in missing_collection:
            collection_object = {
                "organizationId": self.organisation_id,
                "name": collection,
                "externalId": collection,
            }
            json_collection = json.dumps(collection_object).encode("utf-8")
            json_encoded = base64.b64encode(json_collection)
            create_collection = subprocess.Popen(
                [
                    self.cli_executable_path,
                    "create",
                    "org-collection",
                    "--organizationid",
                    self.organisation_id,
                    "--session",
                    self.__session_token,
                    json_encoded,
                ],
                shell=False,
                stdout=subprocess.PIPE,
                text=True,
            )  # nosec B603
            (out, _err) = create_collection.communicate(timeout=15)

            if not _err:
                self.__logger.info(f"Created {collection} successfully")

        self.logout()
