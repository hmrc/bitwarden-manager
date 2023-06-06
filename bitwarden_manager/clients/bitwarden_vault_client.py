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
            return out.decode("utf-8")
        else:
            raise Exception("Failed to login")

    def unlock(self) -> str:
        proc = subprocess.Popen(["./bw", "unlock", self.__password], stdout=subprocess.PIPE, shell=False)  # nosec B603
        (out, _err) = proc.communicate()
        if out:
            string = out.decode("utf-8")
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

    def export_vault(self, password: str) -> str:
        if not self.__session_token:
            self.login()
            self.unlock()
        proc = subprocess.Popen(
            ["./bw", "export", "--session", self.__session_token, "--format", "encrypted_json", "--password", password],
            stdout=subprocess.PIPE,
            shell=False,
        )  # nosec B603
        (out, _err) = proc.communicate()
        # TODO remove print
        print("I attempted to export something")
        print(out)
        return "Placeholder"
