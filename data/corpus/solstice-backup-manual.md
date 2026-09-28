---
id: solstice-backup-manual
company: Solstice Systems
doc_type: product_manual
title: CloudVault Backup Tool — User Manual
version: "2.0"
effective_date: 2025-02-15
status: current
supersedes: null
---

## Overview
CloudVault is Solstice Systems' file backup agent. It runs as a background service and uploads changed files to the customer's configured storage bucket on a schedule.

## Supported Platforms
CloudVault supports Windows 10/11 and macOS 12 or later. There is no Linux agent; Linux hosts must use the CloudVault command-line uploader instead, which lacks the scheduling UI.

## Scheduling Backups
Backups can be scheduled hourly, daily, or weekly from the CloudVault dashboard. The default schedule for new installs is daily at 2:00 AM local time. Manual "Backup Now" runs are always available regardless of schedule.

## Restore Procedure
To restore files, open the CloudVault dashboard, select a snapshot by date, and choose "Restore to original location" or "Restore to new folder." Restores of more than 50 GB require confirmation because they can take several hours.

## Encryption
All data is encrypted client-side with AES-256 before upload, using a key derived from the account's recovery passphrase. Solstice does not store the passphrase and cannot recover data if it is lost.

## Troubleshooting Failed Backups
A failed backup most often means the local disk is full or the recovery passphrase was changed without updating the agent. Check the agent log at the path shown in Settings > Diagnostics > Log Location. If the log shows repeated `AUTH_EXPIRED` errors, re-authenticate the agent from the dashboard.

## Support Contact
Support requests go through the customer portal ticket form. There is no phone support. Typical first response time is one business day.
