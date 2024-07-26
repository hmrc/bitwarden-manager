# Bitwarden Manager

This code helps automate the administration of bitwarden orgs.
Its intended use is to be run in AWS Lambda and to consume user related events

## Example events

Below are the events that this lambda accepts

### New user

Sending this event will invite a new user to the org and onboard them to appropriate collections.
If the user already exists within BitWarden then the lambda will log this.

```json
{
    "event_name": "new_user",
    "username": "test.user01",
    "email": "test.user01@example.com"
}
```

This passes the `username` to the user-management portal (an internal API) which retrieves each user's assigned teams.

Subsequently, a group & collection is associated per corresponding team to the new user within BitWarden.
The user is granted `edit` privileges on the group/collection they're assigned to.
More information regarding access control can be found here [Bitwarden Access Control](https://bitwarden.eu/help/user-types-access-control/#permissions)

`role` is optional. Omitting or setting it to `user` or `super_admin` will invite the user as a `Regular User` while 
setting it to `team_admin` or `all_team_admin` will invite them as a `Manager`. 
See https://bitwarden.eu/help/user-types-access-control/ for more information on role permissions in Bitwarden.

### Update User Groups

Reconcile an existing user's Bitwarden groups and collections with their team membership in UMP. 

This is currently run ad-hoc when a user moves team. It does not remove the user from any custom groups or 
collections that have been manually created in Bitwarden.

```json
{
    "event_name": "update_user_groups",
    "username": "test.user01",
    "email": "test.user01@example.com",
}
```

### Remove user

Sending this event will remove a user from the Bitwarden organisation, revoke his/her access to collections 
and all group memberships within the organisation.
If the user is no longer a member of the Bitwarden organisation, the lambda will log this.

```json
{
    "event_name": "remove_user",
    "username": "test.user01"
}
```

The `username` is the same as the user's `username` in the user-management portal.

### Export Vault

Sending this event will take a backup of all the **org** secrets in the vault, encrypt with the supplied password
and upload it to the bucket name defined in the env var - `BITWARDEN_BACKUP_BUCKET`.

```json
{
  "event_name": "export_vault"
}
```

### Confirm User

This event is triggered via an EventBridge schedule. This iterates through all users in the **org** & confirms
any that match the criteria.

#### Confirmation Criteria

- Email address domain matches `ALLOWED_DOMAINS` environment variable
- User has been invited to & subsequently accepted the invite to said organisation

```json
{
  "event_name": "confirm_user"
}
```

### Expired invites

Bitwarden invites expire after 5 days if not accepted by the user. To handle this, when a user is added to Bitwarden 
via the `New User` event, they are added to a 
[DynamoDB](https://github.com/hmrc/platsec-terraform/blob/main/components/lambda_bitwarden_manager/dynamodb.tf) table in
 PlatSec Production (or Development) account which tracks the number of invites for each user. A 
[daily job](https://github.com/hmrc/platsec-terraform/blob/main/components/lambda_bitwarden_manager/lambda.tf#L36) 
checks this table and reinvites users whose invites have expired and who have not yet had a "reinvite". Users whose 
reinvites have expired without being accepted are removed from Bitwarden, the assumption being that they do not 
currently need it. Users that have been removed from Bitwarden in this way will still be present in the DynamoDB table.

## Environment Variables

- `ALLOWED_DOMAINS` - accepts comma delimited `string`
- `BITWARDEN_CLI_TIMEOUT` - accepts numeric `string`
- `BITWARDEN_BACKUP_BUCKET` - accepts `string`

## averageDailyLogins & averageDailyUniqueUserLogins metrics

See [events-log-parser script](scripts/events-log-parser/README.md), to get averageDailyLogins and
averageDailyUniqueUserLogins metrics from a Bitwarden events log file

## License

This code is open source software licensed under the Apache 2.0 License.
