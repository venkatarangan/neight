# Privacy Policy for Neight

**Last updated: April 28, 2026**

## Overview

Neight is a lightweight text editor for Windows and macOS. This Privacy Policy describes how the application handles information. The short version: **Neight does not collect, transmit, or share any personal data or usage information.**

---

## Data Collection

**Neight does not collect any data.** The application does not:

- Collect personal information of any kind
- Transmit usage statistics, analytics, or telemetry
- Send crash reports or diagnostics to any server
- Track how you use the application
- Access your documents or files beyond what you explicitly open within the app

This has been verified by a code review of the application source. There are no calls to analytics SDKs, crash-reporting services, advertising networks, or any remote data collection endpoints.

---

## Local Data Storage

Neight stores the following information **locally on your device only**:

- **Settings file** (`settings.json` or `config.json`) — stores your preferences such as font name, font size, word wrap preference, and autosave interval. This file is stored on your Mac and never leaves your device.

No data from this file is ever transmitted anywhere.

---

## Network Access

Your text is never transmitted anywhere. Neight has no servers, no account system, and no analytics. There are exactly three situations in which it touches the network.

### In response to something you do

1. **"Search with Google"** — when you select text and choose to search Google, Neight constructs a Google search URL and opens it in your default web browser. No data passes through Neight's servers; the request goes directly from your browser to Google. Google's own privacy policy applies to that search.

2. **URL validation** — when you use the "Insert Hyperlink" feature and ask the app to validate a URL, Neight makes a HEAD request to the URL you entered to check whether it is reachable. This request is made from your device directly to the target URL; no data is routed through any Neight server.

### Automatically, unless you turn it off

3. **Update check on launch** — about five seconds after the window appears, Neight asks the GitHub Releases API whether a newer version has been published.

   - **What is sent:** an ordinary HTTPS GET request to `https://api.github.com/repos/venkatarangan/neight/releases/latest`, carrying only what any HTTPS request carries — your IP address and a `User-Agent` of `Neight-UpdateChecker/1.0`. No document text, no file names, no settings, no identifier of any kind.
   - **What is received:** the latest published release tag.
   - **Timing and failure:** once per launch, with a 10-second timeout. If it fails for any reason it is silently ignored — no dialog, no retry.
   - **What you see:** nothing at all unless a newer version exists, in which case a dot appears next to the Help menu.
   - **How to turn it off:** **Settings → Check for Updates on Launch**. With it unchecked, Neight makes no network connection unless you explicitly ask it to, including via **Help → Check for Updates**.

Apart from these, Neight makes no background or automatic network connections.

---

## Third-Party Services

Neight does not integrate with any third-party analytics, advertising, or data-collection services.

---

## Children's Privacy

Neight does not collect any information from anyone, including children under the age of 13.

---

## Changes to This Policy

If the application is updated in a way that changes how data is handled, this Privacy Policy will be updated and the "Last updated" date above will be revised.

---

## Contact

This application is developed and maintained by Venkatarangan Thirumalai. For questions about this Privacy Policy, please open an issue on the [GitHub repository](https://github.com/venkatarangan/neight).
