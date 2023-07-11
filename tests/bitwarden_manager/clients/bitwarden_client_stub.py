#!/usr/bin/env python3
import sys

if __name__ == "__main__":
    match sys.argv[1]:
        case "login":
            stdout = "You are logged in!\n\nTo unlock your vault, use the `unlock` command. ex:\n$ bw unlock"
            stderr = ""
            returncode = 0
        case "logout":
            stdout = "You have logged out."
            stderr = ""
        case "unlock":
            stdout = "Unlocked"
            stderr = ""
            returncode = 0
        case "export":
            stdout = ""
            stderr = ""
            returncode = 0
        case "create":
            stdout = "Collection successfully created"
            stderr = ""
            returncode = 0
        case _:
            stdout = ""
            stderr = "unknown command"
            returncode = 1
    sys.stdout.write(stdout)
    sys.stderr.write(stderr)
    sys.exit(returncode)
