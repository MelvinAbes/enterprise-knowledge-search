# Incident Response Guide

## Detection and Triage

Monitoring alerts, support reports, and security signals enter the same triage queue. The
on-call engineer groups related events by service and time window, then records the first known
symptom and affected capability.

## Severity

A critical incident causes broad customer impact, data loss, or an active security compromise.
A high-severity incident significantly degrades a production service without a safe workaround.
Repeated errors without user impact begin at medium severity.

## Suspicious Authentication Sequence

Five failed sign-in attempts followed by a successful privileged sign-in within ten minutes are
treated as a suspicious sequence. The responder revokes active sessions, preserves relevant
authentication logs, and contacts the security duty engineer.

## Timeline and Communication

The incident lead maintains a timestamped timeline of decisions, mitigations, and observed
changes. Status updates distinguish verified facts from working hypotheses.

## Closure

An incident closes only after service health is stable, follow-up work has owners, and retained
evidence has an approved storage location.
