# Bitwarden Manager

This code helps automate the administration of bitwarden orgs.
Its intended use is to be run in AWS Lambda and to consume user related events

## Example events

Below are the events that this lambda accepts  

### New user

Sending this event will invite a new user to the org.
If the user already exists within BitWarden then the lambda will log this.

```json
{
    "event_name": "new_user",
    "username": "test.username",
    "email": "test-email@example.com"
}
```

This passes the `username` to the user-management portal (an internal API) to retrieves the users assigned teams.

Subsequently, a group & collection is associated to the new user within BitWarden.
The user is granted `edit` privileges on the group/collection they're assigned to.
More information regarding access control can be found here [Bitwarden Access Control](https://bitwarden.com/help/user-types-access-control/#permissions)

### Export Vault

Sending this event will take a backup of all the **org** secrets in the vault, encrypt with the supplied password
and upload it to the bucket name defined in the env var - `BITWARDEN_BACKUP_BUCKET`.

```json
{
  "event_name": "export_vault"
}
```

## averageDailyLogins & averageDailyUniqueUserLogins metrics

See [events-log-parser script](scripts/events-log-parser/README.md), to get averageDailyLogins and
averageDailyUniqueUserLogins metrics from a Bitwarden events log file

## License

This code is open source software licensed under the Apache 2.0 License.
