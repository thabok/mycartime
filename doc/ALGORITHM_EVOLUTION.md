# From a greedy heuristic to a CP-SAT solver

This is the history of how driving plans get calculated, for anyone
wondering why the codebase looks the way it does: a `solver_service.py` and
no `algorithm_service.py`, even though older commits, issues, or design docs
(`algorithm-improvement-plan.md`, `algorithm-with-solver.md`) still talk
about "the algorithm" and "the greedy engine".

## The original approach: a five-phase greedy heuristic

The first implementation (`algorithm_service.py`, now removed) built a
driving plan in five sequential phases: group members into time-slot pools,
pick a driver per pool (smallest/most-constrained pools first), rebalance
drivers who ended up over quota by looking for a "savior" to swap in,
add extra driver parties from underused members to relieve overcrowded
pools, then fill every party with passengers one at a time.

It worked, and for a while it was the only engine. But it had two compounding
flaws:

1. **Non-determinism.** Python randomizes string-hash order per process
   (`PYTHONHASHSEED`), and the algorithm iterated over `set`-typed
   collections of member initials at several real decision points. The same
   input could silently produce a different plan just because the backend
   process happened to restart - 50 replays of one real capture produced 25
   distinct plans. This was fixed (see `algorithm-improvement-plan.md`) by
   sorting every such iteration and adding explicit tie-break keys, but that
   fix only bought *repeatability*, not *quality*.

2. **A structurally short-sighted search.** The algorithm is greedy and
   single-pass: once it commits to a driver for a pool, it never
   reconsiders that choice in light of what a later pool, possibly on the
   same day, turns out to need. Phase 3 ("rebalance") patches over some of
   this after the fact, but it can only swap in a savior it happens to find
   in the same pool - it can't see the whole 10-day cycle at once, because
   nothing in the design does. A concrete, confirmed case on a real capture
   showed this locking in a provably worse plan (85 vs. 83 total drives, 7
   vs. 5 people over quota) purely because an early, locally-cheap driver
   pick turned out to be globally redundant once a later pool's real needs
   became known.

### Why more heuristics couldn't fix it

The natural next step - smarter tie-break rules, better savior-selection
heuristics, more lookahead in the driver-selection scoring - was tried and
hit diminishing returns fast. Every additional heuristic is another
hand-tuned rule that has to correctly anticipate every other rule's
interaction with it, on every possible input shape. One "smarter" tie-break
heuristic added during this investigation didn't discriminate correctly
between candidates and had to be reverted; it made a specific case better
and an unrelated case worse. This isn't a coincidence: a member's total
`drive_count` across all ten half-days is what the fairness metrics
(`MAX_DRIVES_*`, "over 4/5/6 times") apply to, and no per-day, no-backtracking
greedy pass can see that global picture no matter how good its tie-breaks
are. Greedy, single-pass algorithms are structurally the wrong tool for a
global assignment problem like this one - the fix isn't a better heuristic,
it's a different kind of algorithm.

## The replacement: an OR-Tools CP-SAT solver

`solver_service.py` models the whole 10-day cycle as a single constraint
program: who drives each leg, who rides with whom, and an explicit objective
function that mirrors the same fairness/quality metrics the greedy engine
was informally trying to approximate (never exceed `max_drives` unless
truly unavoidable; minimize the number of people driving more than 6, then
5, then 4 times; minimize total drives; prefer fewer, fuller cars). See
`algorithm-with-solver.md` for the full modeling writeup.

This isn't a smarter heuristic bolted onto the same approach - it replaces
tie-break guesswork with a solver that can consider the entire assignment at
once and prove that no better one exists, given the constraints as modeled.
It resolved the "Ot/Gr" regression case above outright (83 drives / 5 over
quota, matching the provable optimum) without any manual override, and it is
now the only plan-generation engine - the greedy engine, its tests, and its
determinism-specific tooling have all been removed rather than kept as a
fallback, since the solver has no failure mode that a worse heuristic would
meaningfully recover from (see `app.py`'s `_run_plan_engine`: an infeasible
model surfaces as a normal validation error instead).

### How the solver performs in practice

CP-SAT's search generally finds the true optimum (or something
indistinguishable from it) within the first few seconds on a realistic
member set (~20 people, 10 half-days). What takes much longer - minutes, on
a real capture - is *proving* that no better solution exists, i.e. exhausting
the remaining search space after the optimum is already the best-known
solution. Nobody actually needs that proof to get a good plan, so
`config.SOLVER_STOP_AFTER_NO_IMPROVEMENT_SECONDS` (default 5 seconds) stops
the search once it has gone that long without finding a better solution and
serves the best one found so far. In the common case this means: the plan
you get after ~5-10 seconds is very likely the actual optimum, just not
formally proven to be one - a trade worth making, since the alternative is
waiting minutes for a proof of something that was already true.

A result that stops this way (or via the user pressing Stop, or the
`SOLVER_MAX_TIME_SECONDS` wall-clock safety net) is marked as such
(`status=FEASIBLE` rather than `OPTIMAL`, and `stoppedForNoImprovement` in
the solve stats) and is not guaranteed to be reproducible run-to-run, since
it depends on real elapsed time rather than solely on the model and a fixed
random seed. A full `OPTIMAL` result, in contrast, is fully deterministic
(see `backend/test/test_determinism_solver.py`).
