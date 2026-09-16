# Glossary (English)

Use these terms consistently — they match the labels used in the UI.

- **Member** (also "Carpool Party Member", "Person"): a teacher who
  participates in the carpool group.
- **Driving Plan**: the full 2-week ("Week A" + "Week B") carpool
  schedule, made up of one **Day Plan** per weekday per week.
- **Day Plan**: the schedule for a single weekday within one week (A or
  B) — the set of **Parties** for that day's schoolbound and homebound
  journeys.
- **Party**: a group of people traveling together for one direction on
  one day: one **Driver** plus zero or more **Passengers**.
- **Driver**: the person driving for a given party.
- **Passenger**: a person riding with a driver for a given party. The
  same person can be a driver on one journey (e.g. schoolbound) and a
  passenger on the other (homebound) on the same day, but never driver and
  passenger for the *same* journey.
- **Mandatory Driver** (`isDesignatedDriver`): a person who must drive on
  a given day because nobody else arrives/leaves at a compatible time —
  shown with a flag icon in the UI.
- **Solo Driver** / **Lonely Driver** (`isLonelyDriver`): a driver whose
  party must have zero passengers for that journey (from a `Skip AM`/`Skip
  PM` custom preference).
- **Schoolbound**: the morning journey to school.
- **Homebound**: the afternoon/evening journey home.
- **Week A / Week B**: the two-week rotation the driving plan covers.
- **Custom Day / Custom Preferences**: per-member, per-day overrides of
  the timetable-derived schedule. Flags: **Skip** (excluded entirely that
  day), **Needs Car** (must drive), **Skip AM** / **Skip PM** (solo driver
  for that journey, implies Needs Car), **No Wait PM** (homebound party
  time must exactly match this person's end time, no tolerance).
- **Time Tolerance**: the default 30-minute window used to group members
  with similar-but-not-identical start/end times into the same party.
- **Algorithm Phase**: the driving-plan generation stage that created or
  changed a given party — Phase 2 (initial driver selection), Phase 3
  (rebalancing members driving too often), Phase 4 (adding drivers to
  relieve overcrowded parties).
- **Timetable**: the WebUntis-derived schedule (start/end times per day)
  for a member, before any custom preferences are applied.
