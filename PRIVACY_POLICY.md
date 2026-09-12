# Privacy Policy for CarpoolPlanner

_Last updated: 2026-09-12_

## Overview

CarpoolPlanner ("the App") is a desktop application that helps a group of colleagues (e.g. teachers) organize carpool driving schedules. The App runs locally on your device and is designed to keep your data under your control. This policy explains what data the App collects, how it is stored, and when it is shared with third-party services.

## Data We Collect and Store

All data described below is stored **locally on your device**, in your operating system's application data folder. CarpoolPlanner does not operate its own server or database, and does not collect or receive your data.

We store the following categories of data, entered by you or your organization's administrator:

- **Carpool member information**: first names, last names, initials, number of car seats, and part-time status of the people included in the carpool group.
- **Driving preferences**: per-day settings such as days off, "needs a car" flags, custom start/end times, and solo driving preferences.
- **School timetable account credentials** (optional): if you connect a WebUntis account, your WebUntis username and password are stored so the App can retrieve class schedules used to determine pickup/drop-off times.
- **Generated driving plans**: the schedules produced by the App, including who drives whom and at what times. You may export these plans as files (JSON or image) which are then saved wherever you choose on your device.
- **AI assistant conversations** (optional): if you use the built-in AI assistant to adjust a plan, your messages and the relevant plan data are processed as described below.
- **Feedback submissions** (optional): if you use the in-app feedback form, the title and description you write are sent to the developer as described below.

We do not collect names, addresses, email addresses, or precise location data beyond what you voluntarily enter as described above.

## How Your Data Is Stored

- Data is kept in local files on your device (e.g. `user_settings.json`, a local cache of timetable data, and log files), not on a remote server.
- Sensitive values — your WebUntis password and any AI assistant API key you provide — are encrypted at rest using industry-standard symmetric encryption (Fernet/AES), with the encryption key stored separately from the encrypted data.
- This encryption protects your credentials from casual exposure, such as when copying files or creating backups. It does not protect against someone who already has full access to your unlocked device.
- Log files may contain diagnostic information about App operation but do not include your credentials.

## Third-Party Services

Certain optional features send limited data to third-party services in order to function. No data is sent to these services unless you actively use the corresponding feature.

| Feature | Third party | Data sent | Purpose |
|---|---|---|---|
| Timetable import | WebUntis (your school's WebUntis server) | Your WebUntis username and password | To authenticate and retrieve class schedules |
| AI assistant | Anthropic (Claude API) | Your chat messages and the current carpool member list/plan | To generate suggestions for adjusting the driving plan |
| Feedback form | GitHub (via the developer's account) | The title and description text you submit | To create a support/feedback issue for the developer to review |

Each of these third parties processes data under their own privacy policies:
- WebUntis: refer to your school's WebUntis instance / Untis's own privacy policy.
- Anthropic: https://www.anthropic.com/legal/privacy
- GitHub: https://docs.github.com/en/site-policy/privacy-policies/github-privacy-statement

The AI assistant feature requires you to supply your own Anthropic API key (or use a locally installed Claude CLI); no AI assistant data is sent unless you configure and use this feature.

## Data Sharing

We do not sell, rent, or share your data with advertisers or data brokers. Data is only transmitted to the third parties listed above, and only when you use the corresponding optional feature.

## Telemetry and Analytics

CarpoolPlanner does not include any analytics, telemetry, or crash-reporting services. We do not track your usage of the App.

## Data Retention and Deletion

All data is stored locally under your control. You can delete your data at any time by:
- Removing members, preferences, or credentials within the App, or
- Deleting the App's local data folder, or
- Uninstalling the App.

Because CarpoolPlanner does not operate a server, we do not retain any copy of your data once you delete it locally.

## Children's Privacy

CarpoolPlanner is intended for use by adults coordinating carpool logistics (e.g. school staff) and is not directed at children. We do not knowingly collect data from children.

## Changes to This Policy

We may update this privacy policy from time to time to reflect changes in the App. The "Last updated" date above indicates when this policy was last revised.

## Contact

If you have questions about this privacy policy or how your data is handled, please contact the developer via https://github.com/thabok/mycartime/issues
