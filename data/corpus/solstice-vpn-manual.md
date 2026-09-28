---
id: solstice-vpn-manual
company: Solstice Systems
doc_type: product_manual
title: SecureLink VPN Client — User Manual
version: "3.2"
effective_date: 2025-04-01
status: current
supersedes: null
---

## Overview
SecureLink is Solstice Systems' desktop VPN client for Windows, macOS and Linux. It establishes an encrypted tunnel to a Solstice gateway using WireGuard as the default protocol, with OpenVPN available as a fallback for networks that block UDP.

## Installation
Download the installer from the Solstice customer portal. On Windows and macOS, run the installer and accept the network extension prompt. On Linux, install the provided `.deb` or `.rpm` package, which registers a systemd service named `securelink`.

## Login and Authentication
SecureLink requires a company SSO login on first launch. Sessions are cached for 12 hours. Two-factor authentication is enforced automatically if the organization has 2FA enabled in the admin console; there is no per-user opt-out.

## Split Tunneling
Split tunneling is supported starting in version 3.0. When enabled, traffic to addresses listed in the "excluded routes" panel bypasses the VPN tunnel and goes directly to the local network. Split tunneling is off by default and must be turned on in Settings > Network > Split Tunneling.

## Troubleshooting Connection Drops
If the connection drops repeatedly, first check that the device clock is within 5 minutes of actual time, since certificate validation fails on clock skew. Next, switch the protocol from WireGuard to OpenVPN in Settings > Protocol, which resolves drops caused by UDP throttling on some ISPs. If drops continue, capture a diagnostic bundle via Help > Export Diagnostics and open a support ticket.

## Uninstalling
On Windows, uninstall via Settings > Apps. On macOS, drag the app to Trash and run the included `uninstall.sh` script to remove the network extension. On Linux, use the system package manager to remove the `securelink` package.

## Support Contact
Support requests go through the customer portal ticket form. There is no phone support. Typical first response time is one business day.
