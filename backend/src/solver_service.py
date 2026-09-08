"""
CP-SAT based driving-plan engine.

Builds a *single* OR-Tools CP-SAT model spanning the whole 10-day cycle and
lets the solver optimize an explicit objective, rather than picking drivers
pool-by-pool and reconciling fairness afterwards (the approach the retired
greedy heuristic used - see doc/ALGORITHM_EVOLUTION.md). That matters because
the objective couples days together - a member's `drive_count` across all ten
half-days is what `MAX_DRIVES_*` and the over-4/5/6 quality metrics apply to,
and the week A/B similarity goal couples each weekday to its counterpart five
days later, so no per-day greedy pass can see the global picture.

See algorithm-with-solver.md for the modeling rationale.

Determinism: the model is built by iterating *sorted* member/day/direction
lists only (never a `set`), and the solver runs single-threaded with a fixed
random seed, so the same input yields byte-identical output regardless of
PYTHONHASHSEED - as long as the search runs to completion (status OPTIMAL).
A solve that is cut short, either by the user pressing Stop, by the
no-improvement stall timeout, or by the wall-clock safety net, returns
whatever the best solution was at that instant and is therefore *not*
reproducible; that is an accepted trade-off, since proving optimality takes
minutes on a real member set. See backend/test/test_determinism_solver.py.

Progress: proving optimality is slow enough that the UI streams intermediate
results, so callers can pass a `progress_callback` (invoked with a metrics dict
on every improving solution) and a `stop_event` (set it to have the solver
return its current best). See app.py's /api/v1/drivingplan/stream.
"""
import logging
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

from ortools.sat.python import cp_model

import config
from models import DayOfWeekABCombo, DrivingPlan, Member, Party
from plan_builder import PlanBuilder
from utils import (WEEKDAY_NAMES, get_earliest_time, get_latest_time,
                   times_within_tolerance)

logger = logging.getLogger(__name__)

DIRECTIONS = ("schoolbound", "homebound")
DAY_NAMES_SHORT = ["mon", "tue", "wed", "thu", "fri", "mon", "tue", "wed", "thu", "fri"]

# Distinguishes "caller said nothing, use the config default" from an explicit
# `None`, which means "disable the no-improvement stall timeout entirely".
_USE_CONFIG_DEFAULT = object()


class SolverInfeasibleError(RuntimeError):
    """Raised when CP-SAT finds no feasible plan at all (see app.py's fallback)."""


class _ProgressReporter(cp_model.CpSolverSolutionCallback):
    """
    Reports the quality metrics of every improving solution CP-SAT finds, so a
    long solve can show its work instead of looking hung. The metrics are the
    same ones analyze_plans.py computes for a finished plan, which lets the UI
    show "the plan we'd give you if you pressed Stop right now".
    """

    def __init__(self, variables: dict, started_at: float, report: Callable[[dict], None]):
        super().__init__()
        self._variables = variables
        self._started_at = started_at
        self._report = report
        self.solution_count = 0
        self.last_metrics: Optional[dict] = None
        # Read from the watcher thread to implement the no-improvement stall
        # timeout; plain float assignment is atomic under the GIL, so no lock
        # is needed for this single-writer/single-reader pattern.
        self.last_improvement_at = started_at

    def on_solution_callback(self) -> None:
        self.solution_count += 1
        self.last_improvement_at = time.monotonic()
        drive_count = self._variables['drive_count']
        over_n = self._variables['over_n']
        counts = [self.Value(drive_count[i]) for i in sorted(drive_count)]

        self.last_metrics = {
            'solutionCount': self.solution_count,
            'totalDrives': sum(counts),
            'maxDrives': max(counts) if counts else 0,
            'numDrivingMoreThan4': sum(self.Value(over_n[(i, 4)]) for i in sorted(drive_count)),
            'numDrivingMoreThan5': sum(self.Value(over_n[(i, 5)]) for i in sorted(drive_count)),
            'numDrivingMoreThan6': sum(self.Value(over_n[(i, 6)]) for i in sorted(drive_count)),
            'numOverMaxDrives': sum(
                1 for i in sorted(self._variables['overflow'])
                if self.Value(self._variables['overflow'][i]) > 0
            ),
            'driverLegs': sum(
                self.Value(self._variables['is_driver'][k])
                for k in sorted(self._variables['is_driver'])
            ),
            'weekABMismatches': sum(
                self.Value(self._variables['week_ab_mismatch'][k])
                for k in sorted(self._variables['week_ab_mismatch'])
            ),
            'weekABCountImbalance': sum(
                self.Value(self._variables['week_ab_excess'][i])
                for i in sorted(self._variables['week_ab_excess'])
            ),
            'objective': self.ObjectiveValue(),
            'bestObjectiveBound': self.BestObjectiveBound(),
            'elapsedSeconds': time.monotonic() - self._started_at,
        }
        try:
            self._report(self.last_metrics)
        except Exception:  # a broken progress sink must never abort the solve
            logger.warning("Progress callback raised; continuing solve", exc_info=True)


class SolverService:
    """Builds driving plans with an OR-Tools CP-SAT model."""

    def __init__(self, tolerance_minutes: int = None, max_time_in_seconds: float = None,
                 stop_after_no_improvement_seconds=_USE_CONFIG_DEFAULT,
                 progress_callback: Callable[[dict], None] = None,
                 stop_event: 'threading.Event' = None):
        self.tolerance = tolerance_minutes or config.TIME_TOLERANCE_MINUTES
        self.max_time_in_seconds = max_time_in_seconds or config.SOLVER_MAX_TIME_SECONDS
        self.stop_after_no_improvement_seconds = (
            config.SOLVER_STOP_AFTER_NO_IMPROVEMENT_SECONDS
            if stop_after_no_improvement_seconds is _USE_CONFIG_DEFAULT
            else stop_after_no_improvement_seconds
        )
        self.progress_callback = progress_callback
        self.stop_event = stop_event
        self.weights = config.SOLVER_OBJECTIVE_WEIGHTS
        self.members: Dict[str, Member] = {}
        # (day_num, direction) -> {initials: effective time}, sorted by initials
        self._times: Dict[Tuple[int, str], Dict[str, int]] = {}
        self.last_solve_stats: Dict[str, object] = {}

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def calculate_driving_plan(self, members: List[Member]) -> DrivingPlan:
        logger.info("=" * 80)
        logger.info(f"STARTING CP-SAT DRIVING PLAN CALCULATION FOR {len(members)} MEMBERS")
        logger.info("=" * 80)

        self.members = {m.initials: m for m in members}

        self._validate_custom_days(members)

        for member in members:
            member.max_drives = config.MAX_DRIVES_PARTTIME if member.is_part_time else config.MAX_DRIVES_FULLTIME
            member.drive_count = 0
            member.driving_days = set()

        self._collect_presence()

        model, variables = self._build_model()
        solution = self._solve(model, variables)

        parties_by_day = self._extract_parties(solution, variables)
        self._apply_drive_counts(parties_by_day)

        driving_plan = self._build_driving_plan(members, parties_by_day)

        logger.info("=" * 80)
        logger.info("CP-SAT DRIVING PLAN CALCULATION COMPLETE")
        logger.info("=" * 80)
        return driving_plan

    # ------------------------------------------------------------------
    # Input preparation
    # ------------------------------------------------------------------

    def _validate_custom_days(self, members: List[Member]) -> None:
        """Same up-front custom-day validation the greedy engine does."""
        validation_errors = []
        for member in members:
            for day_num in range(10):
                errors = member.validate_custom_day(day_num)
                if errors:
                    validation_errors.extend([f"{member.initials}: {err}" for err in errors])

        if validation_errors:
            error_msg = "Custom day validation failed:\n" + "\n".join(validation_errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        logger.info("✓ Custom day validation passed")

    def _collect_presence(self) -> None:
        """
        Determine, per (day, direction), which members travel and at what
        effective time. Members without a usable time for a leg (or ignored
        entirely) simply get no variables at all, which keeps the model small.
        """
        self._times = {}
        for day_num in range(10):
            for direction in DIRECTIONS:
                schoolbound = direction == "schoolbound"
                times: Dict[str, int] = {}
                for initials in sorted(self.members):
                    member = self.members[initials]
                    if member.should_ignore_on_day(day_num):
                        continue
                    time = (member.get_effective_start_time(day_num) if schoolbound
                            else member.get_effective_end_time(day_num))
                    if time is None:
                        continue
                    times[initials] = time
                self._times[(day_num, direction)] = times

        total = sum(len(t) for t in self._times.values())
        logger.info(f"Presence collected: {total} member-legs across 10 days x 2 directions")

    def _capacity(self, initials: str, day_num: int, schoolbound: bool) -> int:
        """Passenger seats available if this member drives this leg (0 when driving solo)."""
        member = self.members[initials]
        solo = (member.solo_am_on_day(day_num) if schoolbound
                else member.solo_pm_on_day(day_num))
        if solo:
            return 0
        return max(0, member.number_of_seats - 1)

    def _can_carry(self, passenger: str, driver: str, day_num: int, schoolbound: bool) -> bool:
        """
        Whether `driver` may carry `passenger` on this leg, mirroring the greedy
        engine's `_find_best_party_for_passenger` admission rules:
        - the passenger's own tolerance (0 when noWaitingAfternoon, homebound)
          measured against the driver's time, and
        - homebound: never make a noWaitingAfternoon member depart late.
        """
        p_time = self._times[(day_num, "schoolbound" if schoolbound else "homebound")][passenger]
        d_time = self._times[(day_num, "schoolbound" if schoolbound else "homebound")][driver]

        tolerance = self.members[passenger].get_tolerance_for_direction(
            day_num, schoolbound, self.tolerance
        )
        if not times_within_tolerance(p_time, d_time, tolerance):
            return False

        if not schoolbound:
            # A noWaitingAfternoon driver must leave at their exact end time, so no
            # passenger who finishes later may join them.
            if self.members[driver].no_waiting_afternoon_on_day(day_num) and p_time > d_time:
                return False
            # Symmetrically, a noWaitingAfternoon passenger must not be made to wait
            # for a driver who finishes later.
            if self.members[passenger].no_waiting_afternoon_on_day(day_num) and d_time > p_time:
                return False

        return True

    # ------------------------------------------------------------------
    # Model building
    # ------------------------------------------------------------------

    def _build_model(self):
        model = cp_model.CpModel()

        # is_driver[(initials, day, direction)]
        is_driver: Dict[Tuple[str, int, str], cp_model.IntVar] = {}
        # rides_with[(passenger, driver, day, direction)]
        rides_with: Dict[Tuple[str, str, int, str], cp_model.IntVar] = {}
        # drives_on_day[(initials, day)]
        drives_on_day: Dict[Tuple[str, int], cp_model.IntVar] = {}

        for day_num in range(10):
            for direction in DIRECTIONS:
                schoolbound = direction == "schoolbound"
                present = self._times[(day_num, direction)]
                initials_list = sorted(present)

                for initials in initials_list:
                    is_driver[(initials, day_num, direction)] = model.NewBoolVar(
                        f"drives_{initials}_{day_num}_{direction}"
                    )

                for passenger in initials_list:
                    for driver in initials_list:
                        if passenger == driver:
                            continue
                        if self._capacity(driver, day_num, schoolbound) == 0:
                            continue
                        if not self._can_carry(passenger, driver, day_num, schoolbound):
                            continue
                        rides_with[(passenger, driver, day_num, direction)] = model.NewBoolVar(
                            f"rides_{passenger}_with_{driver}_{day_num}_{direction}"
                        )

                # Exactly-one-role: every present member either drives or rides along.
                for initials in initials_list:
                    options = [is_driver[(initials, day_num, direction)]]
                    options += [rides_with[key] for key in sorted(rides_with)
                                if key[0] == initials and key[2] == day_num and key[3] == direction]
                    model.AddExactlyOne(options)

                # Capacity, and "you can only be ridden with if you actually drive".
                for driver in initials_list:
                    carried = [rides_with[key] for key in sorted(rides_with)
                               if key[1] == driver and key[2] == day_num and key[3] == direction]
                    if not carried:
                        continue
                    capacity = self._capacity(driver, day_num, schoolbound)
                    model.Add(sum(carried) <= capacity * is_driver[(driver, day_num, direction)])

                # needsCar: this member must drive every leg they are present for.
                for initials in initials_list:
                    if self.members[initials].needs_car_on_day(day_num):
                        model.Add(is_driver[(initials, day_num, direction)] == 1)

                if not schoolbound:
                    self._add_no_waiting_afternoon_constraints(
                        model, rides_with, day_num, initials_list
                    )

        # A member who drives to school has their car there, so they must drive home
        # too - the greedy engine enforces the same thing (VALIDATION 1 rejects any
        # plan where someone is a driver in one direction and a passenger in the other
        # on the same day).
        for initials in sorted(self.members):
            for day_num in range(10):
                sb = (initials, day_num, "schoolbound")
                hb = (initials, day_num, "homebound")
                if sb in is_driver and hb in is_driver:
                    model.Add(is_driver[sb] == is_driver[hb])

        # drives_on_day / drive_count / quota variables
        drive_count: Dict[str, cp_model.IntVar] = {}
        overflow: Dict[str, cp_model.IntVar] = {}
        over_n: Dict[Tuple[str, int], cp_model.IntVar] = {}

        for initials in sorted(self.members):
            member = self.members[initials]
            day_vars = []
            for day_num in range(10):
                legs = [is_driver[(initials, day_num, direction)]
                        for direction in DIRECTIONS
                        if (initials, day_num, direction) in is_driver]
                if not legs:
                    continue
                day_var = model.NewBoolVar(f"drives_on_day_{initials}_{day_num}")
                model.AddMaxEquality(day_var, legs)
                drives_on_day[(initials, day_num)] = day_var
                day_vars.append(day_var)

            count = model.NewIntVar(0, len(day_vars), f"drive_count_{initials}")
            model.Add(count == sum(day_vars))
            drive_count[initials] = count

            # Soft max_drives: exceeding is allowed but heavily penalized, matching the
            # greedy engine's "degrade rather than fail" fallback.
            over = model.NewIntVar(0, 10, f"overflow_{initials}")
            model.Add(over >= count - member.max_drives)
            overflow[initials] = over

            for threshold in (4, 5, 6):
                flag = model.NewBoolVar(f"over_{threshold}_{initials}")
                model.Add(count >= threshold + 1).OnlyEnforceIf(flag)
                model.Add(count <= threshold).OnlyEnforceIf(flag.Not())
                over_n[(initials, threshold)] = flag

        # Not part of the objective (the over-4/5/6 tiers already drive fairness);
        # kept so the busiest member's load can be logged after each solve.
        max_drives_var = model.NewIntVar(0, 10, "max_drives")
        for initials in sorted(drive_count):
            model.Add(max_drives_var >= drive_count[initials])

        week_ab_mismatch, week_ab_excess = self._build_week_ab_similarity(model, drives_on_day)

        self._add_objective(model, is_driver, drive_count, over_n, overflow,
                            week_ab_mismatch, week_ab_excess)

        variables = {
            'is_driver': is_driver,
            'rides_with': rides_with,
            'drives_on_day': drives_on_day,
            'drive_count': drive_count,
            'overflow': overflow,
            'over_n': over_n,
            'week_ab_mismatch': week_ab_mismatch,
            'week_ab_excess': week_ab_excess,
            'max_drives': max_drives_var,
        }
        logger.info(
            f"Model built: {len(is_driver)} driver vars, {len(rides_with)} ride vars, "
            f"{len(drives_on_day)} day vars, {len(week_ab_mismatch)} week-A/B mismatch vars"
        )
        return model, variables

    def _add_no_waiting_afternoon_constraints(self, model, rides_with, day_num, initials_list) -> None:
        """
        A noWaitingAfternoon passenger must not be made to wait for *anyone* in
        their car, which is a three-way condition (passenger, driver, co-passenger)
        that `_can_carry` can't express pairwise: forbid a noWait passenger and a
        later-finishing co-passenger from sharing the same driver.
        """
        times = self._times[(day_num, "homebound")]
        no_wait = [i for i in initials_list
                   if self.members[i].no_waiting_afternoon_on_day(day_num)]
        if not no_wait:
            return

        for driver in initials_list:
            for passenger in no_wait:
                key_p = (passenger, driver, day_num, "homebound")
                if key_p not in rides_with:
                    continue
                for other in initials_list:
                    if other in (passenger, driver):
                        continue
                    if times[other] <= times[passenger]:
                        continue
                    key_o = (other, driver, day_num, "homebound")
                    if key_o not in rides_with:
                        continue
                    model.AddBoolOr([rides_with[key_p].Not(), rides_with[key_o].Not()])

    def _build_week_ab_similarity(self, model, drives_on_day):
        """
        Secondary goal: give each member the same driving *weekdays* in week A and
        week B, so they only have to remember one pattern ("I drive Mondays and
        Thursdays") instead of two.

        Two penalties per member:
        - `mismatch`: one bool per weekday the member drives in exactly one of the
          two weeks. Only built where the member travels on *both* of the paired
          weekdays - being absent one week is a fact of their timetable rather
          than a scheduling choice, so it must not read as a mismatch.
        - `excess`: how far `|week A drives - week B drives|` exceeds one. An odd
          total cannot split evenly over two weeks, so a swing of one is
          unavoidable and stays free; only wider swings (3-and-1 where 2-and-2
          was possible) are penalized. This is what separates "drives on the
          wrong days" from "drives a lopsided number of days".
        """
        mismatch: Dict[Tuple[str, int], cp_model.IntVar] = {}
        excess: Dict[str, cp_model.IntVar] = {}

        for initials in sorted(self.members):
            week_a_days, week_b_days = [], []

            for weekday in range(5):
                a_var = drives_on_day.get((initials, weekday))
                b_var = drives_on_day.get((initials, weekday + 5))
                if a_var is not None:
                    week_a_days.append(a_var)
                if b_var is not None:
                    week_b_days.append(b_var)
                if a_var is None or b_var is None:
                    continue
                flag = model.NewBoolVar(f"week_ab_mismatch_{initials}_{weekday}")
                model.Add(a_var + b_var == 1).OnlyEnforceIf(flag)
                model.Add(a_var == b_var).OnlyEnforceIf(flag.Not())
                mismatch[(initials, weekday)] = flag

            if not week_a_days or not week_b_days:
                continue  # travels in only one of the two weeks - nothing to balance

            diff = model.NewIntVar(-5, 5, f"week_ab_diff_{initials}")
            model.Add(diff == sum(week_a_days) - sum(week_b_days))
            abs_diff = model.NewIntVar(0, 5, f"week_ab_absdiff_{initials}")
            model.AddAbsEquality(abs_diff, diff)

            # Same hinge trick as `overflow`: a lower bound is all that's needed,
            # since minimizing pins the variable to max(0, abs_diff - 1).
            over = model.NewIntVar(0, 4, f"week_ab_excess_{initials}")
            model.Add(over >= abs_diff - 1)
            excess[initials] = over

        return mismatch, excess

    def _add_objective(self, model, is_driver, drive_count, over_n, overflow,
                       week_ab_mismatch, week_ab_excess) -> None:
        """
        One weighted sum whose weights are separated by large enough gaps that the
        terms behave lexicographically, ordered to match `analyze_plans.py`'s
        `score()`: over-6, over-5, over-4, then week A/B similarity - with
        hard-ish preferences (max_drives overflow, drivingSkip) on top.

        Nothing here rewards less driving. Keeping members inside their
        MAX_DRIVES is the whole quality story; a member driving *below* their
        quota is not an improvement, so plans that differ only in total drives
        or car count are deliberately scored equal (see config's note).
        """
        w = self.weights
        # Each tier is (weight_key, [vars]); tiers are listed highest priority first.
        tiers: List[Tuple[str, list]] = []

        tiers.append(('overflow', [overflow[i] for i in sorted(overflow)]))

        # Driving on a day the member asked to skip is a last resort. It stays a
        # penalty rather than a hard constraint because forbidding it outright can
        # make a leg unsatisfiable (e.g. two mutually-compatible drivingSkip members
        # travelling alone), and the greedy engine allows it in that case too.
        despite_prefs = []
        for key in sorted(is_driver):
            initials, day_num, _direction = key
            custom = self.members[initials].get_custom_day(day_num)
            if custom and custom.driving_skip and not custom.needs_car:
                despite_prefs.append(is_driver[key])
        tiers.append(('drives_despite_prefs', despite_prefs))

        for threshold, weight_key in ((6, 'over_6'), (5, 'over_5'), (4, 'over_4')):
            tiers.append((weight_key, [over_n[(i, threshold)] for i in sorted(drive_count)]))

        # Same weekdays in both weeks, ranked below over-4/5/6 so week-to-week
        # regularity can never be bought at the price of an extra frequent driver.
        tiers.append(('week_ab_mismatch',
                      [week_ab_mismatch[key] for key in sorted(week_ab_mismatch)]))
        tiers.append(('week_ab_count_imbalance',
                      [week_ab_excess[i] for i in sorted(week_ab_excess)]))

        self._warn_if_tiers_not_lexicographic(tiers)

        model.Minimize(sum(w[key] * var for key, tier in tiers for var in tier))

    def _warn_if_tiers_not_lexicographic(self, tiers) -> None:
        """
        The weighted sum only *behaves* lexicographically while each tier's weight
        exceeds the worst-case total of every tier below it. That holds for
        realistic member counts but not for arbitrarily large ones, so check it
        against this instance's actual variable bounds instead of assuming.
        """
        w = self.weights
        worst_below = 0
        for key, tier in reversed(tiers):
            weight = w[key]
            if tier and weight <= worst_below:
                logger.warning(
                    f"Objective tier '{key}' (weight {weight}) does not dominate the "
                    f"worst-case total of lower-priority tiers ({worst_below}) for this "
                    f"input size - plan quality ordering may not be strictly "
                    f"lexicographic. Consider raising config.SOLVER_OBJECTIVE_WEIGHTS."
                )
            worst_below += weight * sum(var.proto.domain[-1] for var in tier)
        if worst_below > 2 ** 62:
            logger.warning(
                f"Objective upper bound {worst_below} is approaching CP-SAT's int64 "
                f"limit; lower config.SOLVER_OBJECTIVE_WEIGHTS for inputs this large."
            )

    # ------------------------------------------------------------------
    # Solving
    # ------------------------------------------------------------------

    def _solve(self, model, variables) -> cp_model.CpSolver:
        solver = cp_model.CpSolver()
        # Single-threaded with a fixed seed: required for run-to-run determinism.
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = config.SOLVER_RANDOM_SEED
        solver.parameters.max_time_in_seconds = self.max_time_in_seconds

        started_at = time.monotonic()
        reporter = _ProgressReporter(
            variables, started_at, self.progress_callback or (lambda _metrics: None)
        )

        # StopSearch() is safe to call from another thread and takes effect within
        # the current search step, so neither a Stop press nor a stall timeout has
        # to wait for the next improving solution to arrive.
        finished = threading.Event()
        stopped_for_stall = threading.Event()

        def watch_for_stop():
            while not finished.wait(config.SOLVER_STOP_POLL_SECONDS):
                if self.stop_event is not None and self.stop_event.is_set():
                    logger.info("Stop requested - asking CP-SAT for its current best")
                    solver.StopSearch()
                    return
                if (self.stop_after_no_improvement_seconds is not None
                        and reporter.solution_count > 0):
                    idle_for = time.monotonic() - reporter.last_improvement_at
                    if idle_for >= self.stop_after_no_improvement_seconds:
                        logger.info(
                            f"No improving solution for {idle_for:.1f}s (limit "
                            f"{self.stop_after_no_improvement_seconds:.1f}s) - asking "
                            f"CP-SAT for its current best"
                        )
                        stopped_for_stall.set()
                        solver.StopSearch()
                        return

        watcher = threading.Thread(target=watch_for_stop, daemon=True,
                                   name='solver-stop-watcher')
        watcher.start()

        try:
            status = solver.Solve(model, reporter)
        finally:
            finished.set()
            watcher.join(timeout=1.0)

        status_name = solver.StatusName(status)
        solved = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        self.last_solve_stats = {
            'status': status_name,
            'objective': solver.ObjectiveValue() if solved else None,
            'bestObjectiveBound': solver.BestObjectiveBound() if solved else None,
            'wallTime': solver.WallTime(),
            'solutionCount': reporter.solution_count,
            'stopped': self.stop_event is not None and self.stop_event.is_set(),
            'stoppedForNoImprovement': stopped_for_stall.is_set(),
            'metrics': reporter.last_metrics,
        }
        logger.info(
            f"CP-SAT finished: status={status_name}, "
            f"objective={self.last_solve_stats['objective']}, "
            f"solutions={reporter.solution_count}, "
            f"wallTime={solver.WallTime():.2f}s"
        )

        if not solved:
            raise SolverInfeasibleError(
                f"CP-SAT produced no usable solution (status={status_name})"
            )
        logger.info(
            f"Busiest member drives {solver.Value(variables['max_drives'])} of 10 days"
        )
        if status == cp_model.FEASIBLE:
            reason = ("no improving solution found for "
                      f"{self.stop_after_no_improvement_seconds:.1f}s" if stopped_for_stall.is_set()
                      else "wall-clock/stop limit reached")
            logger.warning(
                f"CP-SAT stopped before proving optimality after {solver.WallTime():.1f}s "
                f"({reason}) - serving the best solution found so far. This result is "
                f"good but unproven, and not guaranteed to be reproducible."
            )
        return solver

    # ------------------------------------------------------------------
    # Solution -> Party/DayPlan/DrivingPlan
    # ------------------------------------------------------------------

    def _extract_parties(self, solver, variables) -> Dict[int, Dict[str, List[Party]]]:
        is_driver = variables['is_driver']
        rides_with = variables['rides_with']

        parties_by_day: Dict[int, Dict[str, List[Party]]] = {
            day_num: {"schoolbound": [], "homebound": []} for day_num in range(10)
        }

        for day_num in range(10):
            for direction in DIRECTIONS:
                schoolbound = direction == "schoolbound"
                times = self._times[(day_num, direction)]

                passengers_by_driver: Dict[str, List[str]] = {}
                for key in sorted(rides_with):
                    passenger, driver, key_day, key_direction = key
                    if key_day != day_num or key_direction != direction:
                        continue
                    if solver.Value(rides_with[key]):
                        passengers_by_driver.setdefault(driver, []).append(passenger)

                for initials in sorted(times):
                    key = (initials, day_num, direction)
                    if not solver.Value(is_driver[key]):
                        continue

                    member = self.members[initials]
                    passengers = sorted(passengers_by_driver.get(initials, []))
                    driver_time = times[initials]

                    member_times = [driver_time] + [times[p] for p in passengers]
                    party_time = (get_earliest_time(member_times) if schoolbound
                                  else get_latest_time(member_times))

                    custom = member.get_custom_day(day_num)
                    solo = (member.solo_am_on_day(day_num) if schoolbound
                            else member.solo_pm_on_day(day_num))

                    parties_by_day[day_num][direction].append(Party(
                        day_of_week_ab_combo=None,  # filled in when the DayPlan is built
                        driver=initials,
                        time=party_time,
                        passengers=passengers,
                        is_designated_driver=member.needs_car_on_day(day_num),
                        drives_despite_custom_prefs=bool(custom and custom.driving_skip),
                        schoolbound=schoolbound,
                        is_lonely_driver=solo,
                        pool_name=self._pool_name(day_num, direction, driver_time),
                        original_driver_time=driver_time,
                    ))

        return parties_by_day

    def _pool_name(self, day_num: int, direction: str, time: int) -> str:
        """Builds a human-readable pool identifier for the Party's pool_name field."""
        week = "a" if day_num < 5 else "b"
        return f"solver-{DAY_NAMES_SHORT[day_num]}-{week}-{direction}-{time:04d}-tol{self.tolerance}"

    def _apply_drive_counts(self, parties_by_day) -> None:
        """Populate the runtime Member fields the summary and callers expect."""
        for member in self.members.values():
            member.drive_count = 0
            member.driving_days = set()

        for day_num in range(10):
            drivers_today = set()
            for direction in DIRECTIONS:
                for party in parties_by_day[day_num][direction]:
                    drivers_today.add(party.driver)
            for initials in sorted(drivers_today):
                member = self.members[initials]
                member.driving_days.add(day_num)
                member.drive_count += 1

    def _build_driving_plan(self, members: List[Member], parties_by_day) -> DrivingPlan:
        """
        Uses PlanBuilder for the TimeInfo construction and VALIDATION 1/2/3
        checks shared with (nothing else now, but previously also) the greedy
        engine, so downstream consumers see the same DrivingPlan shape.
        """
        builder = PlanBuilder(self.members, parties_by_day)

        day_plans = {}
        for day_num in range(10):
            day_of_week_ab = DayOfWeekABCombo(
                day_of_week=WEEKDAY_NAMES[day_num % 5],
                is_week_a=day_num < 5,
                unique_number=day_num + 1,
            )
            day_plans[day_num + 1] = builder.build_day_plan(day_num, day_of_week_ab)

        summary = builder.generate_summary(members)
        member_id_map = {m.initials: m.id for m in members if getattr(m, 'id', None) is not None}

        return DrivingPlan(summary=summary, day_plans=day_plans, member_id_map=member_id_map)
