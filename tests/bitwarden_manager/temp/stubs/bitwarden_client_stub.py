#!/usr/bin/env python3
import json
import os
import pathlib
import sys
from time import sleep

TIMEOUT = int(os.environ.get("BITWARDEN_CLI_TIMEOUT", 0))

if TIMEOUT:
    sleep(TIMEOUT + 1)

with open(pathlib.Path(__file__).parent.joinpath("./list_collection_items.json")) as f:
    list_collection_items_output = json.load(f)


def fail_if_no_session_set() -> None:
    if not os.environ.get("BW_SESSION", None):
        raise Exception(
            "BW_SESSION env var is missing, we want to provide the session token via env var so that it "
            "does not apper in the output of any stack trace"
        )


if __name__ == "__main__":
    match sys.argv[1]:
        case "login":
            stdout = "You are logged in!\n\nTo unlock your vault, use the `unlock` command. ex:\n$ bw unlock"
            stderr = ""
            return_code = 0
        case "logout":
            stdout = "You have logged out."
            stderr = ""
            return_code = 0
        case "unlock":
            stdout = "unlocked thisisatoken"
            stderr = ""
            return_code = 0
        case "list":
            fail_if_no_session_set()
            stdout = json.dumps(list_collection_items_output)
            stderr = ""
            return_code = 0
        case _:
            stdout = ""
            stderr = "unknown command"
            return_code = 1
    sys.stdout.write(stdout)
    sys.stderr.write(stderr)
    sys.exit(return_code)
