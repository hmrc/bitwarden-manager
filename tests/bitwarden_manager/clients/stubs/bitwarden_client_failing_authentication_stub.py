#!/usr/bin/env python3
import sys

if __name__ == "__main__":
    match sys.argv[1]:
        case "login":
            sys.stdout.write("")
            sys.stderr.write("Something went wrong. Try again.")
            sys.exit(1)
        case "config":  # we want tests to pass this stage to surface other errors
            sys.stdout.write("Saved setting `config`.")
            sys.stderr.write("")
            sys.exit(0)
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
