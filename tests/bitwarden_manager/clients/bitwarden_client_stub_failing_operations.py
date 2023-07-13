#!/usr/bin/env python3
import json
import os
import sys

bad_list_user_output = [
    {
        "object": "org-member",
        "email": "example@example.co.uk",
        "name": "Invited User",
        "id": "EA5FF022-5490-43D4-9D2A-34CE7AFBB1F8",
        "status": 0,
        "type": 2,
        "twoFactorEnabled": True,
    },
    {
        "object": "org-member",
        "email": "example@example.co.uk",
        "name": "Accepted User",
        "id": "8DF75F8A-5F45-409B-B179-47757FF70D7E",
        "status": 1,
        "type": 2,
        "twoFactorEnabled": True,
    },
    {
        "object": "org-member",
        "email": "example2@example.co.uk",
        "name": "Confirmed User",
        "id": "8019DFF6-DCAF-440A-A4D3-61C37A35EF52",
        "status": 2,
        "type": 2,
        "twoFactorEnabled": True,
    },
    {
        "object": "org-member",
        "email": "example@example.co.uk",
        "name": "Revoked User",
        "id": "8BE1F247-1604-4FB9-B392-C99ADFA3B2C6",
        "status": -1,
        "type": 2,
        "twoFactorEnabled": True,
    },
]

if __name__ == "__main__":
    match sys.argv[1]:
        case "login":  # we want tests to pass this stage to surface other errors
            sys.stdout.write("You are logged in!\n\nTo unlock your vault, use the `unlock` command. ex:\n$ bw unlock")
            sys.stderr.write("")
            sys.exit(0)
        case "unlock":  # we want tests to pass this stage to surface other errors
            sys.stdout.write("You have unlocked")
            sys.stderr.write("")
            sys.exit(0)
        case _:
            sys.stderr.write("This is an fake error")
            sys.exit(1)
