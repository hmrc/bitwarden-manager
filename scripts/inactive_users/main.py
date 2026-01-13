# flake8: noqa
import csv

import requests
import certifi
import time

bw_vault_uri = "https://api.bitwarden.eu"
bw_client_id = "CLIENT_ID"
bw_client_secret = "SECRET"
protected_user_emails = [
    "ben.lovatt@digital.hmrc.gov.uk",
    "chris.wright@digital.hmrc.gov.uk",
    "jamie.gibbs@digital.hmrc.gov.uk",
    "marcus.mee@digital.hmrc.gov.uk",
    "nerea.harries@digital.hmrc.gov.uk",
]
USE_API = len(bw_client_id) > 10 and len(bw_client_secret) == 10


def get_active_users():
    users = []
    counter = 0
    try:
        with open("bitwarden_org-events_export.csv") as fp:
            stream = csv.DictReader(fp, delimiter=",")
            for active_user in stream:
                if len(active_user.get('userEmail', '')) > 0 and active_user.get('userEmail', '') not in users:
                    users.append(active_user.get('userEmail', ''))
                    counter += 1
    except FileNotFoundError:
        print("No org-events export found. Run user audit report and save as bitwarden_org-events_export.csv")
    print(f"Found {counter} active users")
    return users


def get_auth_token():
    response = requests.post(
        "https://identity.bitwarden.eu/connect/token",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=('grant_type=client_credentials&scope=api.organization'
              f'&client_id={bw_client_id}&client_secret={bw_client_secret}')
    )

    if response.status_code != requests.codes.ok:
        raise Exception(response.json())

    return response.json()['access_token']


def get_all_members():
    members = []

    if USE_API:
        print(certifi.where())
        # https://bitwarden.com/help/api/
        response = requests.get(
            bw_vault_uri + "/public/members",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {get_auth_token()}"
            }
        )

        if response.status_code != requests.codes.ok:
            raise Exception(response.json())

        for member in response.json()['data']:
            members.append(member)
    else:
        print("Using local file")
        try:
            with (open("bitwarden_member-access_export.csv") as fp):
                stream = csv.DictReader(fp, delimiter=",")
                for _user in stream:
                    if (
                            len(_user.get('Email', '')) > 0
                            and
                            {'email': _user.get('Email', '')} not in members
                    ):
                        members.append({'email': _user.get('Email', '')})
        except FileNotFoundError:
            print(
                "No member-access export found.Run member access report and save as bitwarden_member-access_export.csv")
    print(f"Found {len(members)} members")
    return members


def get_inactive_user_emails(_active_users, _all_members):
    inactive_member_emails = []

    for member in _all_members:
        inactive_member_emails.append(member['email'])

    for active_user in _active_users:
        try:
            inactive_member_emails.remove(active_user)
        except ValueError:
            print(f"Active user {active_user} not found in member list")

    return sorted(inactive_member_emails)


def offboard_inactive_members(_all_members, inactive_member_emails):
    users_to_offboard = []

    for member in _all_members:
        if member['email'] not in protected_user_emails:
            if member['email'] in inactive_member_emails:
                users_to_offboard.append(member)
        else:
            print(f"Member {member['email']} in protected user list")

    auth_token = get_auth_token()
    for user in users_to_offboard:
        print(f"Offboarding user {user['email']}")
        uid = user['id']
        response = requests.delete(
            bw_vault_uri + "/public/members/" + uid,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_token}"
            }
        )

        if response.status_code != requests.codes.ok:
            try:
                json_response = response.json()
            except Exception:
                raise Exception(f"Error offboarding user {user['email']}: {response.text}")

            raise Exception(json_response)

        print(f"Offboarding user {user['email']} complete")
        time.sleep(3)


if __name__ == "__main__":
    active_users = get_active_users()
    all_members = get_all_members()
    inactive_user_emails = get_inactive_user_emails(active_users, all_members)
    if USE_API:
        offboard_inactive_members(all_members, inactive_user_emails[:100])

    print("Active:", len(active_users), "Total:", len(all_members), "Inactive:", len(inactive_user_emails))

    # for user in sorted(inactive_user_emails):
    #   print(user)
