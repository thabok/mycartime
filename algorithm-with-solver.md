# Driving-plan algorithm: introducing an OR-Tools CP-SAT solver

## Background / motivation

`backend/src/algorithm_service.py` builds driving plans with a five-phase
greedy heuristic (pool creation -> driver selection -> rebalancing ->
additional drivers -> passenger filling). [algorithm-improvement-plan.md](algorithm-improvement-plan.md)
made that heuristic **deterministic** (no more hash-seed-dependent output),
but determinism only guarantees *repeatability*, not *quality*. A concrete,
confirmed case (see conversation history, "Ot/Gr" case on a real capture)
showed the greedy algorithm locking in a provably worse plan (85 vs. 83
total drives, 7 vs. 5 people over quota) because an early, locally-cheap
driver pick turned out to be globally redundant once a later, same-day pool's
real needs became known. Fixing this class of problem with more tie-break
heuristics has diminishing returns and real regression risk (already
observed once this session: a "smarter" tie-break heuristic didn't
discriminate correctly and had to be reverted) - greedy, single-pass,
no-backtracking algorithms are structurally the wrong tool for this kind of
global assignment problem.

**Goal of this plan**: introduce Google OR-Tools' CP-SAT constraint
solver as an alternative (and eventually primary) engine that finds a
*provably optimal or near-optimal* plan for a given input, replacing
greedy heuristics and their tie-break guesswork with an explicit objective
function.

## Why CP-SAT specifically

- The problem is combinatorial (who drives, who rides with whom, which
  pool absorbs which passengers) with hard constraints (seat capacity,
  time tolerance, `needsCar`, `soloAm`/`soloPm`, `noWaitingAfternoon`,
  `ignoreCompletely`, `maxDrives`) and a multi-part objective (minimize
  total drives, minimize count of people over 4/5/6 drives, minimize max
  drives, prefer tighter/fuller pools) - a textbook fit for CP-SAT rather
  than an LP/MIP relaxation or a bespoke search.
- CP-SAT is **deterministic** by default for a fixed model, fixed
  parameters (notably `num_search_workers=1`), and fixed OR-Tools version -
  which matters a lot here, since determinism was the entire subject of the
  prior work and must not regress.
- It's free, MIT-licensed, actively maintained, has a mature Python API,
  and typical driving-plan instances here are small (≈20 members x 10
  half-days ≈ 200 "trips" to assign) - well within CP-SAT's comfort zone
  for sub-second-to-low-seconds solve times.

## High-level modeling approach

Model **one day-direction at a time is not enough** - the objective
couples days together (a member's total `drive_count` across all 10
half-days is what `MAX_DRIVES_FULLTIME`/`MAX_DRIVES_PARTTIME` and the
over-4/5/6 metrics apply to). So the model must be a **single CP-SAT model
spanning the whole 10-day cycle** for one member-set, not 10 independent
per-day models. This is the main structural change vs. today's algorithm,
which processes pools/days mostly independently and only reconciles
drive-count fairness after the fact (Phase 3/4).

### Decision variables

For each `(day, direction)` where `direction ∈ {schoolbound, homebound}`:

- For each member `m` who is present that day/direction and `can_drive_on_day`:
  `is_driver[m, day, direction]: BoolVar` - whether `m` drives this leg.
- For each ordered pair `(passenger p, candidate driver m)` where `p != m`,
  both present, and `m` could plausibly carry `p` (time within `m`'s
  tolerance for that direction): `rides_with[p, m, day, direction]: BoolVar`.
- Each present member is *either* a driver *or* a passenger of exactly one
  driver, per (day, direction) - see constraints below.
- `drive_count[m]: IntVar` = sum of `is_driver[m, day, *]` OR-ed across
  direction per day (a member "drives" that day if they drive *either*
  leg; CP-SAT can model this with an auxiliary `drives_on_day[m, day]`
  bool linked to both directions via `AddMaxEquality` or simple
  impl590ications, matching the existing `drive_count`/`driving_days`
  semantics in `Member`).
- `over_4[m]`, `over_5[m]`, `over_6[m]: BoolVar` linked to `drive_count[m]`
  via `AddLinearConstraint`/reification, to compute the same
  `numDrivingMoreThan{4,5,6}` metrics `analyze_plans.py` already reports.
- `max_drives_var: IntVar`, constrained to be `>= drive_count[m]` for all
  `m` (models `maxDrives`).

### Hard constraints (mirroring current Member/Party semantics)

- **Presence**: only variables for `(m, day, direction)` where `m` has a
  valid effective time that day/direction (`get_effective_start_time`/
  `get_effective_end_time` non-null, `should_ignore_on_day` false) exist at
  all.
- **Exactly-one role**: for every present `(m, day, direction)`,
  `is_driver[m,day,dir] + sum_over_drivers(rides_with[m, driver, day, dir]) == 1`.
- **Capacity**: for every candidate driver `m`,
  `sum_p rides_with[p, m, day, dir] <= (number_of_seats[m] - 1) * is_driver[m,day,dir]`.
- **Time tolerance**: `rides_with[p, m, day, dir]` can only be `True` if
  `p`'s effective time is within `m`'s tolerance window for that
  direction (`get_tolerance_for_direction`) - encoded by simply not
  creating the variable for incompatible pairs (keeps the model small)
  rather than adding a constraint.
- **`needsCar`**: `is_driver[m, day, dir] == 1` forced (both directions)
  when `member.needs_car_on_day(day)`.
- **`solo_am`/`solo_pm`**: if `m` drives and `solo_am_on_day`/`solo_pm_on_day`
  is set for that direction, force `rides_with[*, m, day, dir] == 0` for
  everyone (no passengers allowed) - i.e. cap capacity at 0 instead of
  `seats - 1`.
- **`no_waiting_afternoon`**: for homebound only, forbid `rides_with[p, m]`
  combinations that would push the party's departure time past `m`'s (or
  an already-included no-wait passenger's) exact end time - same logic as
  `_would_break_no_waiting_afternoon`, just expressed as a precomputed
  incompatibility list of `(p, m)` pairs whose `rides_with` var is fixed
  to 0 (or omitted).
- **`drive_count[m] <= max_drives[m]`** as a *soft* constraint (see
  objective) rather than hard, to match the existing algorithm's fallback
  behavior of exceeding max_drives when there is truly no alternative
  (Phase 2's "if no one available within max drives, allow exceeding").
  Model this with a per-member overflow variable
  `overflow[m] = max(0, drive_count[m] - max_drives[m])` and heavily
  penalize it in the objective, rather than an `AddLinearConstraint` upper
  bound - this preserves the existing "never fail to produce a plan, just
  degrade gracefully" property.

### Objective (single weighted sum, mirroring `analyze_plans.py`'s existing
composite quality ordering so "better" means the same thing it already
does when comparing plans)

Minimize, in this **lexicographic-by-large-weight-gaps** order (encode as
one weighted sum with weights separated by large enough multiples that
higher-priority terms always dominate, same trick already used for
`future_mandatory_count * 100` in the current heuristic):

1. `sum(overflow[m])` - never exceed max_drives unless truly unavoidable.
2. `sum(over_6[m])`, then `sum(over_5[m])`, then `sum(over_4[m])` - matches
   `analyze_plans.py`'s `score()` ordering exactly.
3. `sum(drive_count[m])` - total drives (fewer is better, all else equal).
4. Party tightness: minimize number of distinct driver-legs created
   (`sum(is_driver[*])`) as a secondary proxy for "fewer, fuller cars,"
   consistent with `avgCarsPerPool`/`avgOccupancy` in `analyze_plans.py`.

Keep the weight constants in one place (e.g. a `SOLVER_OBJECTIVE_WEIGHTS`
dict in `config.py`) so they can be tuned against real captures without
touching model-building code.

## Integration plan with `algorithm_service.py`

### New module: `backend/src/solver_service.py`

- `class SolverService` with the same public entry point shape as
  `AlgorithmService.calculate_driving_plan(members) -> DrivingPlan`, so it
  is a drop-in alternative, not a rewrite of the callers.
- Internally: build the CP-SAT model as above, call
  `cp_model.CpSolver()` with `parameters.num_search_workers = 1`,
  `parameters.random_seed` fixed, and a bounded `max_time_in_seconds`
  (see "Solve time budget" below), then translate the solved variable
  assignment back into the existing `Party`/`DayPlan`/`DrivingPlan`
  dataclasses so every downstream consumer (frontend, PNG export,
  summary generation) is unaffected.
- Reuse `TimeSlot`/`DriverPool`-style grouping *only* for building the
  candidate `rides_with` variable set efficiently (avoid an O(n^2) blow-up
  by first bucketing members into tolerance-compatible groups, same as
  `_group_members_by_time` does today) - not for the actual assignment
  logic, which the solver owns entirely.

### Selecting which engine runs

- Add `config.PLAN_ENGINE = "greedy" | "solver"` (default `"greedy"`
  initially, flipped once validated).
- `app.py`'s `calculate_driving_plan_logic` picks
  `AlgorithmService` or `SolverService` based on `config.PLAN_ENGINE` -
  a one-line branch, no change to the request/response contract.
- Add a **fallback**: if the solver reports `INFEASIBLE` or times out
  without even a feasible (not necessarily optimal) solution, fall back to
  the greedy `AlgorithmService` for that request and log a warning -
  production must never hard-fail a driving-plan request because of a
  solver edge case.

### Solve time budget

- Set `max_time_in_seconds` conservatively (e.g. 10-15s) for the
  request path; CP-SAT returns the best feasible solution found so far
  when the deadline hits (`solver.Solve()` still returns `FEASIBLE` even
  if not proven `OPTIMAL`), so a timeout degrades to "good but unproven"
  rather than failing.
- Log `solver.StatusName()`, `solver.ObjectiveValue()`, and
  `solver.WallTime()` on every solve for observability, mirroring the
  existing verbose `logger.info` style in `algorithm_service.py`.

## Determinism validation (critical - do not skip)

Reuse the exact infrastructure already built for the greedy algorithm's
determinism fix:

- `backend/src/experiments/replay_capture.py` gets a `--engine solver`
  flag (or a second script `replay_capture_solver.py`) to run
  `SolverService` against a capture the same way.
- `backend/src/experiments/run_batch.py` against the solver path, across
  many fresh `PYTHONHASHSEED` values (hash seed shouldn't matter at all to
  CP-SAT, but Python-side model-building code might still iterate over a
  `set` somewhere by mistake - this is exactly the bug class the earlier
  investigation found three separate instances of, so re-check for it in
  all *new* code too) - assert byte-identical output across 50 trials,
  same as `backend/test/test_determinism.py` already does for the greedy
  path.
- Add a second regression test,
  `backend/test/test_determinism_solver.py`, mirroring the greedy one.

## Quality validation

- Run both engines against the same real capture(s) already in
  `backend/src/captures/`, compare via `analyze_plans.py`'s existing
  metrics, and confirm the solver's plan is at least as good on every
  metric as the greedy baseline (it should be provably optimal or
  near-optimal by construction, but *prove* it against real data before
  trusting it).
- Specifically re-run the "Ot/Gr" case from this session's investigation
  and confirm the solver reaches 83 total drives / 5 over-quota (or
  better) *without* the manual "No Car" override - this is the concrete
  regression test for "did we actually fix the thing we set out to fix."

## Phased rollout

1. **Phase 0 - dependency & scaffold**: add `ortools` to
   `backend/requirements.txt`, create `solver_service.py` with an empty
   model that just proves the plumbing works (build members -> trivial
   model -> `DrivingPlan` round-trip) on one small capture.
2. **Phase 1 - core model**: implement decision variables, hard
   constraints, and a *simple* objective (total drives + overflow only).
   Validate feasibility and correctness (constraint satisfaction, not yet
   quality) against several captures with `_build_day_plan_from_parties`'s
   existing validation logic (VALIDATION 1/2/3 in
   `algorithm_service.py`) reused as-is against the solver's output.
3. **Phase 2 - full objective**: add the over-4/5/6 and tightness terms,
   tune weights against real captures, confirm quality matches or beats
   the greedy baseline on all of `analyze_plans.py`'s metrics.
4. **Phase 3 - determinism proof**: the validation described above (50+
   trials, byte-identical, regression test committed).
5. **Phase 4 - shadow mode**: run the solver alongside the greedy
   algorithm in production for every real request (solver result logged/
   captured but greedy result still served), comparing metrics over real
   traffic for a period before flipping `PLAN_ENGINE` default.
6. **Phase 5 - cutover**: flip the default engine, keep greedy code and
   `PLAN_ENGINE` flag around as an escape hatch for at least one release
   cycle in case of an unanticipated solver edge case in the field.

## Explicitly out of scope for this plan

- Rewriting or removing the greedy algorithm - it stays as a fallback and
  escape hatch indefinitely (see Phase 5).
- Re-tuning `MAX_DRIVES_FULLTIME`/`MAX_DRIVES_PARTTIME` or other
  `config.py` knobs - same constraint as the original determinism plan.
- Multi-objective Pareto exploration / letting users pick a trade-off
  interactively - one fixed weighted objective, matching today's implicit
  single "best plan" behavior.
