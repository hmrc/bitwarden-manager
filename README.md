# Bitwarden Manager

This code helps automate the administration of bitwarden orgs.
Its intended use is to be run in AWS Lambda and to consume user related events

## Example events

Below are the events that this lambda accepts  

### New user

Sending this event will invite a new user to the org.
If the user already exists then the lambda will log this and exit successfully.

```json
{
    "event_name": "new_user",
    "username": "test.username",
    "email": "test-email@example.com"
}
```

### Export Vault

Sending this event will take an backup of all the secrets in the vault, encrypted with the supplied password
and store it in S3 - `arn:aws:s3:::bitwarden-exports-development-7eh4g0`.

```json
{
  "event_name": "export_vault",
  "password": "my_very_secure_password"
}
```

## averageDailyLogins & averageDailyUniqueUserLogins metrics

See [events-log-parser script](scripts/events-log-parser/README.md), to get averageDailyLogins and
averageDailyUniqueUserLogins metrics from a Bitwarden events log file

## License

This code is open source software licensed under the Apache 2.0 License.
