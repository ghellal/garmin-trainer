# Firestore MVP schema

Firestore is accessed by the FastAPI service only. The browser receives no
Firestore data access; `web/firestore.rules` denies all direct client reads and
writes. The API uses the Cloud Run runtime service account and verifies the
Firebase ID token and configured single-user email before accessing data.

Initial collection layout (schema document only; data endpoints arrive in later
roadmap phases):

| Collection | Document ID | MVP contents |
|---|---|---|
| `profiles` | Firebase UID | User preferences, available training days, units, timestamps |
| `goals` | generated ID | Sport, target event/date, measurable target, status |
| `activities` | Garmin activity ID | Normalized summary, source, activity time, sync timestamp |
| `daily_metrics` | ISO date | Normalized sleep/recovery summaries, source and sync timestamp |
| `sessions` | generated ID | Proposed/accepted session, status, target date, data provenance |
| `feedback` | generated ID | Activity reference, RPE, sensations, pain fields, comment, timestamp |
| `conversations` | generated ID | Conversation metadata and update timestamp |
| `conversations/{id}/messages` | generated ID | Role, content, timestamp; retained for the approved 12-month period |
| `coach_memory` | Firebase UID | Explicitly confirmed compact coaching context; no inferred diagnosis |

Garmin data are minimal normalized copies: activity summaries for 24 months and
daily health summaries for 12 months. Raw FIT/GPS/high-frequency streams are
not stored by default. Feedback and confirmed sessions remain until user
deletion. The conversation transcript is retained for 12 months; the compact
coaching memory can be reset independently.

Use server timestamps for writes, store timestamps in UTC, and include a schema
version on documents that may evolve. Firestore TTL policies can later enforce
the rolling retention for daily metrics and chat messages; until configured,
application-level cleanup must be implemented before those retention periods
are considered enforced.
