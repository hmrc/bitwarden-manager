#!/usr/bin/env python3
import os
import sys
from time import sleep

TIMEOUT = int(os.environ.get("BITWARDEN_CLI_TIMEOUT", 0))

if TIMEOUT:
    sleep(TIMEOUT + 1)


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
            stdout = ""
            stderr = "failed"
            return_code = 1
        case _:
            stdout = ""
            stderr = "unknown command"
            return_code = 1
    sys.stdout.write(stdout)
    sys.stderr.write(stderr)
    sys.exit(return_code)
