#!/usr/bin/env python3
import sys

if __name__ == "__main__":
    match sys.argv[1]:
        case "login":
            sys.stdout.write("client_id or client_secret is incorrect. Try again.")
            sys.stderr.write("")
            sys.exit(1)
        case "unlock":
            sys.stdout.write("")
            sys.stderr.write("You are not logged in.")
            sys.exit(1)
        case "logout":
            sys.stdout.write("")
            sys.stderr.write("You are not logged in.")
            sys.exit(1)
        case _:
            sys.stderr.write("This is a fake error")
            sys.exit(1)
