# Driving-plan algorithm: determinism & quality improvement plan

## Background / problem statement

Users have observed that generating a driving plan from the **same
members + same WebUntis timetable data** sometimes produces a noticeably
worse plan than usual (more people driving more than 4/5/6 times, a higher
max-drives outlier) without any input having changed.

### Confirmed root cause

The algorithm (`backend/src/algorithm_service.py`) is only non-deterministic
*across process restarts*, not within a running process. Python randomizes
string-hash order per process by default (`PYTHONHASHSEED`), and a few spots
in the algorithm iterate over `set`-typed collections of member initials,
so restarting the backend changes iteration order and thus tie-breaking,
even for byte-identical input.

This was empirically verified:
- 50 replays of one real captured input (see "Capture infrastructure"
  below), each in its own subprocess (fresh hash seed), produced **25
  distinct plans**.
- Pinning `PYTHONHASHSEED` to a fixed value makes replays 100% reproducible;
  varying it changes the outcome.
- Quality spread observed across those 50 runs:

  | Metric | min | max | mean | stdev |
  |---|---|---|---|---|
  | Total drives | 82 | 85 | 83.6 | 0.87 |
  | # people driving >4x | 4 | 7 | 5.5 | 0.94 |
  | # people driving >5x | 1 | 2 | 1.1 | 0.30 |
  | # people driving >6x | 0 | 1 | 0.04 | — |
  | Max drives (any one person) | 6 | 7 | 6.04 | — |
  | Avg cars/pool (tightness) | 1.76 | 1.83 | 1.80 | 0.02 |
  | Avg occupancy per party | 2.20 | 2.28 | 2.24 | 0.02 |

  Party-tightness/occupancy metrics are stable across runs; the real
  quality swings are in **driver-count fairness** (who ends up over-quota).
  One member (`Wl`) was the top driver in every run (6 drives in 48/50
  runs, 7 drives in 2/50 runs) — a full extra, avoidable drive purely from
  tie-break luck.

### Exact source-code locations of the non-determinism

Traced precisely, not all `set` usage in the file is actually a problem:

- **Confirmed real bug**: `AlgorithmService._rebalance_driving_distribution`
  (`backend/src/algorithm_service.py`, savior-selection block, ~line 987-1005):
  ```python
  potential_saviors = list({
      member_init
      for search_pool in savior_search_pools
      for member_init in search_pool.time_slot.members
      if (...)
  })
  savior_initials = min(
      potential_saviors,
      key=lambda s: (self.members[s].drive_count, -self.members[s].number_of_seats)
  )
  ```
  When two saviors tie on both `drive_count` and `number_of_seats`, `min()`
  silently returns whichever happens to come first in hash order. No
  deterministic tertiary tie-break exists.

- **Unconfirmed suspect (needs empirical check, not assumption)**:
  `TimeSlot.members` (`models`/`algorithm_service.py`, declared as
  `Set[str]`) is iterated to build `pool.candidates` in
  `_create_driver_pools`, and its derived lists (`remaining_to_cover`,
  `uncovered_members`) are iterated in the "mandatory driver" (`needsCar`)
  search inside `_select_drivers_and_create_parties`. This *might* be
  benign (every mandatory driver plausibly gets picked eventually
  regardless of order) but that has not been proven — it must be logged
  and checked, not assumed safe.

- **Confirmed non-issues** (ruled out by tracing, so instrumentation effort
  should skip these): `self.members` is a `dict` built from the input list
  (insertion order preserved, not hash-dependent); pool creation order
  comes from `_group_members_by_time`'s `defaultdict` (dict, insertion-order
  preserved); `_select_best_driver`'s final `candidate_scores.sort()`
  already tie-breaks deterministically by candidate initials (included as
  the last tuple element); Phase 4 (`_add_additional_driver_parties`)
  iterates `self.members.items()` (dict, stable) and sorts pools by a
  ratio with ties resolved by an already-deterministic list order — so
  Phase 4 is not a source of variance.

## Capture / replay infrastructure already in place

These pieces exist in the repo already (built in a prior session) and
should be reused, not rebuilt:

- `backend/src/config.py`: `CAPTURE_PLAN_INPUTS = True`, `CAPTURE_DIR =
  "./captures"`.
- `backend/src/app.py`: `_capture_plan_input(members, start_date_str)`,
  called from `calculate_driving_plan_logic` right after
  `timetable_service.get_timetables_for_members(...)`. Every real
  `/api/v1/drivingplan` request dumps members (incl. custom prefs) and
  resolved per-day WebUntis timetables to
  `backend/src/captures/drivingplan-<timestamp>.json`. Credentials are
  never captured. The directory is gitignored (`**/captures/` in
  `.gitignore`).
- `backend/src/experiments/replay_capture.py`: loads a capture file,
  reconstructs `Member` objects with `.timetable` populated directly (no
  WebUntis call needed), and runs `AlgorithmService().calculate_driving_plan()`
  once, writing the resulting `DrivingPlan.to_dict()` JSON to a given path.
- `backend/src/experiments/run_batch.py`: runs N trials of
  `replay_capture.py`, each in its own subprocess (so each gets a fresh
  `PYTHONHASHSEED`), collecting `plan-NNN.json` files in an output dir.
- `backend/src/experiments/analyze_plans.py`: computes, per plan, drive
  counts per member, counts of people driving >4/>5/>6 times, total
  drives, pool-level tightness (cars-per-pool, avg occupancy), and prints
  a comparison table + summary statistics across all analyzed plans.

A real capture already exists at
`backend/src/captures/drivingplan-20260907-195113-598833.json` (20
members) and was used to produce the numbers above.

## Goal

Replace "run it many times and hope for a good hash seed" with a
deterministic algorithm that reliably produces the *best* known plan for a
given input, by finding and fixing the actual decision points that
currently resolve ties arbitrarily.

## Implementation plan

### Phase 1 — Instrument every tie point (log only, no behavior change)

- At the `potential_saviors` / `min()` call in
  `_rebalance_driving_distribution`: log the full tied candidate set,
  each candidate's `(drive_count, number_of_seats)` score, and which one
  was picked.
- At the "mandatory driver" (`needsCar`) search in both branches of
  `_select_drivers_and_create_parties`: log whenever more than one
  candidate simultaneously qualifies as a mandatory driver in the same
  pool, and which one was picked first.
- Add one more general check: log whenever `_find_best_party_for_passenger`'s
  `min(..., key=lambda p: len(p.passengers))` has more than one party tied
  on passenger count (this affects party/pool grouping, not drive counts,
  but should be confirmed rather than assumed irrelevant).
- Run this instrumented version once per captured input (reuse existing
  captures under `backend/src/captures/`), with logging enabled, to see:
  how many real ties occur per run, whether the "mandatory driver" suspect
  ever actually has a live tie, and whether passenger-assignment ties
  affect anything beyond cosmetic grouping.

Deliverable: a log/report per capture showing the actual tie inventory —
this determines whether Phase 2's search space is as small as expected
(single digits) before building the enumeration harness.

### Phase 2 — Exhaustive enumeration harness (replaces random sampling)

- Build a small harness (e.g.
  `backend/src/experiments/enumerate_ties.py`) that, for one capture:
  1. Runs once with a fixed `PYTHONHASHSEED` to get a baseline tie
     inventory (from Phase 1's logging).
  2. For each real tie found, monkeypatches/parameterizes that specific
     decision so the harness can force each of the tied options in turn,
     while holding everything else fixed (same hash seed, same input).
  3. Produces the full cross-product of tie choices (expected to be at
     most a few dozen combinations, not a combinatorial explosion, since
     Phase 1 is expected to find only single-digit real ties per run).
  4. Runs the algorithm once per combination and saves the resulting plan
     + which choice was made at each tie.

This replaces `run_batch.py`'s N-random-restarts approach for this
specific investigation (that script remains useful for other purposes,
e.g. regression-checking after a fix).

### Phase 3 — Attribution: which choice causes which quality change

- Reuse `analyze_plans.py`'s metrics (or extend it) to score every plan
  produced in Phase 2.
- Because only one tie-choice changes between adjacent combinations, build
  a direct table: `(tie point, chosen candidate, candidate's relevant
  properties) -> resulting metric deltas` (esp. change in max-drives outlier
  and count of people driving >4x). This is causal attribution, not
  correlation across noisy independent runs.
- Identify which property of the tied candidates (e.g. fewer future
  mandatory pools, more remaining flexible days, lower total remaining
  capacity elsewhere) actually predicts the better outcome.

### Phase 4 — Encode the winning rule as a deterministic tie-break

- Add the attributed property as an explicit secondary/tertiary key in the
  `min()`/scoring tuple at each real tie point identified in Phase 1
  (at minimum: `_rebalance_driving_distribution`'s savior selection).
  Always include a final deterministic tiebreak (e.g. candidate initials)
  so no tie is ever left to hash/set order again.
- If Phase 1 finds the "mandatory driver" search or passenger-assignment
  ties are also live (not just theoretical), apply the same treatment
  there.

### Phase 5 — Validation

- Re-run `run_batch.py` (50+ trials, varying process/hash seed) against
  the same captures used above and confirm all trials now produce an
  identical plan for identical input.
- Confirm the now-deterministic plan's quality metrics are at or near the
  best observed in the original 50-run study (not merely "consistent" but
  consistently *good*).
- Add a regression test (e.g. under `backend/test/`) that replays a fixed
  capture under at least two different `PYTHONHASHSEED` values and asserts
  identical output, so this class of bug can't silently regress.

## Explicitly out of scope for this plan

- Changing `MAX_DRIVES_FULLTIME`/`MAX_DRIVES_PARTTIME` or other
  `config.py` tuning knobs — this plan is about removing arbitrary
  variance, not re-tuning target drive counts.
- The "keep randomness, run many times, pick the best" alternative
  discussed and rejected in favor of this deterministic approach.
