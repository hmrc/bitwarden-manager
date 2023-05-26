import subprocess, os
from logging import Logger

class BitwardenVaultClient:
    def __init__(self, logger: Logger, client_id: str, client_secret: str) -> None:
        self.__logger = logger
        self.__client_secret = client_secret
        self.__client_id = client_id
        self.__session_token = ""

    def login(self) -> str:
        tmp_env = os.environ.copy()
        tmp_env["BW_CLIENTID"] = self.__client_id
        tmp_env["BW_CLIENTSECRET"] = self.__client_secret
        proc = subprocess.Popen(["./bw", "login", "--apikey"], stdout=subprocess.PIPE, env=tmp_env, shell=False)
        (out, _err) = proc.communicate()
        if out:
            return out.decode("utf-8")
        else:
            raise Exception("Failed to login")

    def unlock(self, password: str) -> str:
        proc = subprocess.Popen(["./bw", "unlock", password], stdout=subprocess.PIPE, shell=False)
        (out, _err) = proc.communicate()
        if out:
            string = out.decode("utf-8")
            self.__session_token = string.split()[-1]
            return string
        else:
            raise Exception("Failed to unlock")

    def logout(self) -> str:
        proc = subprocess.Popen(["./bw", "logout"], stdout=subprocess.PIPE, shell=False)
        (out, _err) = proc.communicate()
        if out:
            return out.decode("utf-8")
        else:
            raise Exception("Failed to logout")

    def export_vault(self) -> str:
        return "Placeholder"
