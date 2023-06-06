import boto3
import datetime
import subprocess  # nosec B404
import os
from logging import Logger


class BitwardenVaultClient:
    def __init__(self, logger: Logger, client_id: str, client_secret: str, password: str) -> None:
        self.__logger = logger
        self.__client_secret = client_secret
        self.__client_id = client_id
        self.__password = password
        self.__session_token = ""  # nosec B105

    def login(self) -> str:
        tmp_env = os.environ.copy()
        tmp_env["BW_CLIENTID"] = self.__client_id
        tmp_env["BW_CLIENTSECRET"] = self.__client_secret
        proc = subprocess.Popen(
            ["./bw", "login", "--apikey"], stdout=subprocess.PIPE, env=tmp_env, shell=False
        )  # nosec B603
        (out, _err) = proc.communicate()
        if out:
            self.__logger.info("Logged in to Bitwarden Vault")
            return out.decode("utf-8")
        else:
            raise Exception("Failed to login")

    def unlock(self) -> str:
        proc = subprocess.Popen(["./bw", "unlock", self.__password], stdout=subprocess.PIPE, shell=False)  # nosec B603
        (out, _err) = proc.communicate()
        if out:
            string = out.decode("utf-8")
            self.__logger.info("Unlocked Bitwarden Vault")
            self.__session_token = string.split()[-1]
            return string
        else:
            raise Exception("Failed to unlock")

    def logout(self) -> str:
        proc = subprocess.Popen(["./bw", "logout"], stdout=subprocess.PIPE, shell=False)  # nosec B603
        (out, _err) = proc.communicate()
        if out:
            return out.decode("utf-8")
        else:
            raise Exception("Failed to logout")

    def export_vault(self, password: str) -> None:
        self.__logger.info("Exported vault backup to")
        if not self.__session_token:
            self.login()
            self.unlock()
        now = datetime.datetime.now()
        output_path = f"bw_backup_{now}.json"
        proc = subprocess.Popen(
            [
                "./bw",
                "export",
                "--session",
                self.__session_token,
                "--format",
                "encrypted_json",
                "--password",
                password,
                "--ouput",
                f"/tmp/{output_path}",
            ],
            stdout=subprocess.PIPE,
            shell=False,
        )  # nosec B603
        (out, _err) = proc.communicate()
        self.__logger.info(f"Exported vault backup to {output_path}")

    def write_file_to_s3(self, filepath: str) -> None:
        bucket_name = "bitwarden-exports-development-7eh4g0"
        try:
            s3 = boto3.resource("s3")
            s3.Object(bucket_name, filepath).put(Body=open(f"/tmp/{filepath}", "rb"))
        except botocore.exceptions.ClientError as e:
            raise Exception("Failed to write to S3")
