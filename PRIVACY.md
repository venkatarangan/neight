# Privacy Policy for Neight

**Last updated: August 20, 2026**

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

- **Settings file** (`settings.json`) — stores preferences such as font,
  appearance, word wrap, autosave interval, window size, and the last-opened
  file path. On Windows it is normally beside `Neight.exe`, with
  `%LOCALAPPDATA%\Neight\settings.json` used when that folder is not writable.
  On macOS it is stored at
  `~/Library/Application Support/Neight/settings.json`.
- **Saved documents** — are written only to locations you choose. When
  autosave is enabled, Neight updates the chosen document at the selected
  interval.
- **Presets and recovery copies** — are stored in
  `%USERPROFILE%\Documents\Neight\` on Windows and
  `~/Documents/Neight/` on macOS. Recovery copies contain only unsaved text
  from the current document and are removed during normal save, open, new-file,
  and close operations.
- **Autosave diagnostic logs** — are created beside `settings.json` only when
  an autosave write fails or its watchdog reports a problem.

None of these files is transmitted by Neight.

---

## Network Access

Neight never transmits documents automatically. It has no servers, account
system, analytics, or telemetry. Network access occurs only for the actions
below.

### In response to something you do

1. **"Search with Google"** — when you select text and choose to search Google, Neight constructs a Google search URL and opens it in your default web browser. The selected text becomes part of that URL. No data passes through Neight's servers; the request goes directly from your browser to Google. Google's own privacy policy applies to that search.

2. **Sorkuvai lookup** — when you explicitly look up a selected word, Neight
   opens the corresponding search URL in your default browser. The selected
   word becomes part of that URL.

3. **Markdown links** — clicking an external link in the Markdown preview
   opens that address in your default browser.

4. **URL validation** — when you use the "Insert Hyperlink" feature and ask the app to validate a URL, Neight makes a HEAD request to the URL you entered to check whether it is reachable. This request is made from your device directly to the target URL; no data is routed through any Neight server.

5. **Neight Releases page** — choosing **Help → Neight Releases on GitHub** opens that page in your default browser. Neight itself makes no request; it simply hands the address to your browser.

### Automatically

Nothing. **Neight makes no automatic or background network connections at all.**
Every network use is in the list above, and every item on that list happens only
because you clicked something. Neight does not check for updates, does not phone
home, and does not contact any server on its own — at launch or at any other time.

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
