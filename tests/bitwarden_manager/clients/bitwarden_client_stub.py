#!/usr/bin/env python3
import json
import sys

list_user_output = [
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
        case "login":
            stdout = "You are logged in!\n\nTo unlock your vault, use the `unlock` command. ex:\n$ bw unlock"
            stderr = ""
            return_code = 0
        case "logout":
            stdout = "You have logged out."
            stderr = ""
            return_code = 0
        case "unlock":
            stdout = "You have unlocked"
            stderr = ""
            return_code = 0
        case "export":
            stdout = ""
            stderr = ""
            return_code = 0
        case "create":
            stdout = "Collection successfully created"
            stderr = ""
            return_code = 0
        case "list":
            stdout = json.dumps(list_user_output)
            stderr = ""
            return_code = 0
        case "confirm":
            stdout = ""
            stderr = ""
            return_code = 0
        case _:
            stdout = ""
            stderr = "unknown command"
            return_code = 1
    sys.stdout.write(stdout)
    sys.stderr.write(stderr)
    sys.exit(return_code)
