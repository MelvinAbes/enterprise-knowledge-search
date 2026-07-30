# Access Control Policy

## Authentication

Administrative accounts require multi-factor authentication. Shared administrator accounts are
not permitted. Service identities use credentials issued for one workload and one environment.

## Privileged Access

Permanent privileged access is limited to the platform operations group. Temporary elevation
requires an approved change or incident reference and expires automatically after eight hours.
Emergency access is reviewed on the next business day.

## Access Reviews

System owners review privileged roles every quarter. The review removes dormant accounts,
confirms each role has an active owner, and records exceptions with an expiry date.

## Credential Handling

Credentials must not be stored in source control, support tickets, or application logs. A
suspected exposure requires immediate rotation and an incident record.
