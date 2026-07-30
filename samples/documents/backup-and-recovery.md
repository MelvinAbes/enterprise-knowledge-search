# Backup and Recovery Standard

## Purpose

This standard defines recoverability expectations for the fictional Northstar Services
platform. It applies to PostgreSQL databases, object storage, and configuration repositories.

## Backup Schedule

Production databases receive an incremental backup every night at 01:00 UTC. A full backup is
created every Sunday. Configuration repositories are exported after each approved release.

## Retention

Daily backup sets are retained for 30 days. The final full backup of each month is retained for
12 months. Expired backup sets are removed by an automated lifecycle rule.

## Restore Verification

The operations team performs a restore exercise in an isolated environment every month. The
exercise records whether the four-hour recovery-time objective and the 24-hour recovery-point
objective were met. A failed exercise creates a high-severity incident and a corrective action.

## Ownership

The platform operations lead owns this standard. Service teams remain responsible for
documenting service-specific restoration steps.
