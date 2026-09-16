"""
Post-processing pass that improves *how* passengers are grouped into the
parties the solver already decided, without changing who drives.

SolverService's CP-SAT model (see solver_service.py) picks drivers to satisfy
its own objective (fairness, week A/B driver similarity, etc) and is
indifferent between two passengers with the same driver being served by
different same-time parties - any feasible assignment scores the same. That
leaves three cosmetic/quality-of-life gaps for the people living with the
plan that aren't worth encoding as CP-SAT objective terms:

1. A passenger should ride with whichever eligible party's time is closest
   to their own, rather than an arbitrary feasible one (e.g. two 7:45
   parties on the same day when one 7:55 party had room).
2. The same passenger should ride with the same driver in week A and week B
   whenever the schedules allow it, to reduce the mental load of tracking
   different party constellations per week.
3. Passengers should be spread evenly across same-time parties where doing
   so doesn't conflict with 1 or 2 - for a passenger concern 2 just matched
   onto the same driver both weeks, that means moving them to balance load
   only as a synced pair (same new driver, both weeks at once, see
   _balance_even_distribution_synced), never splitting them back apart.

This module re-derives passenger-to-party placement after the fact, one
day+direction at a time, respecting every constraint the solver itself
enforces (solo-am/pm, tolerance, no-waiting-afternoon, seat capacity) - it
only ever moves a passenger between parties that already exist for that
day/direction, never changes a driver, creates/removes a party, or touches a
driver's own time.
"""
import logging
from typing import Dict, List

from models import Member, Party
from party_eligibility import capacity as _capacity, desired_time as _desired_time, \
    distance_minutes as _distance, is_eligible as _is_eligible

logger = logging.getLogger(__name__)

DIRECTIONS = ("schoolbound", "homebound")


def _rebalance_day_direction(parties: List[Party], members: Dict[str, Member],
                              day_num: int, schoolbound: bool, tolerance: int) -> None:
    """
    Re-assigns passengers among `parties` (mutating .passengers in place) to
    prefer the closest-time eligible party first (concern 1).

    Implemented as a Hospital/Residents-style deferred-acceptance matching:
    every passenger already has at least one feasible party - their current
    one, since that's exactly what SolverService._can_carry required to put
    them there - so this always terminates with a feasible,
    capacity-respecting result. It can only move a passenger to a
    *closer*-time party than the status quo, never a worse or infeasible one.
    """
    if len(parties) <= 1:
        return

    passengers = sorted({p for party in parties for p in party.passengers})
    if not passengers:
        return

    capacities = {party.driver: _capacity(members[party.driver], day_num, schoolbound) for party in parties}
    current_driver = {p: party.driver for party in parties for p in party.passengers}

    preferences: Dict[str, List[Party]] = {}
    for passenger in passengers:
        eligible = [party for party in parties
                    if _is_eligible(passenger, party, members, day_num, schoolbound, tolerance)]
        eligible.sort(key=lambda party: (_distance(passenger, party, members, day_num, schoolbound), party.driver))
        preferences[passenger] = eligible

    next_choice_index = {p: 0 for p in passengers}
    accepted: Dict[str, List[str]] = {party.driver: [] for party in parties}
    unplaced = list(passengers)

    while unplaced:
        passenger = unplaced.pop(0)
        prefs = preferences[passenger]
        if next_choice_index[passenger] >= len(prefs):
            # Ran out of proposals (shouldn't happen: the current party is
            # always eligible) - fall back to the status quo.
            accepted[current_driver[passenger]].append(passenger)
            continue

        party = prefs[next_choice_index[passenger]]
        next_choice_index[passenger] += 1
        bucket = accepted[party.driver]
        if len(bucket) < capacities[party.driver]:
            bucket.append(passenger)
            continue

        # Party is full: only displace a passenger who is a strictly worse
        # fit (further from this party's time) than the one proposing.
        candidates = sorted(
            bucket + [passenger],
            key=lambda cand: (_distance(cand, party, members, day_num, schoolbound), cand)
        )
        bucket[:] = candidates[:capacities[party.driver]]
        unplaced.extend(candidates[capacities[party.driver]:])

    for party in parties:
        party.passengers = sorted(accepted[party.driver])


def _unify_week_ab(parties_by_day: Dict[int, Dict[str, List[Party]]],
                    members: Dict[str, Member], tolerance: int) -> set:
    """
    Where a passenger currently rides with different drivers in week A and
    week B (for the same weekday+direction), move them onto the same driver
    in both weeks if that driver drives both weeks and can eligibly and
    feasibly carry them there (concern 2). Never evicts anyone else - only
    applies when the target party already has a free seat, so it can never
    create an infeasible state.

    Returns the set of (day_num, direction, passenger) that ended up unified
    by this pass, so later passes (see _balance_even_distribution) can avoid
    undoing this work.
    """
    unified = set()

    for weekday in range(5):
        day_a, day_b = weekday, weekday + 5
        for direction in DIRECTIONS:
            schoolbound = direction == "schoolbound"
            parties_a = {party.driver: party for party in parties_by_day[day_a][direction]}
            parties_b = {party.driver: party for party in parties_by_day[day_b][direction]}

            driver_of_a = {p: party.driver for party in parties_a.values() for p in party.passengers}
            driver_of_b = {p: party.driver for party in parties_b.values() for p in party.passengers}

            shared_passengers = sorted(set(driver_of_a) & set(driver_of_b))
            for passenger in shared_passengers:
                driver_a, driver_b = driver_of_a[passenger], driver_of_b[passenger]
                if driver_a == driver_b:
                    logger.debug("[ab-unify] %s already has the same driver (%s) both weeks on %s/%s",
                                 passenger, driver_a, weekday, direction)
                    unified.add((day_a, direction, passenger))
                    unified.add((day_b, direction, passenger))
                    continue

                # Option 1: move the passenger onto driver_b's party in week A.
                target = parties_a.get(driver_b)
                if target is None:
                    logger.debug("[ab-unify] %s on %s/%s: %s (week-B driver) doesn't drive week A - "
                                 "no option 1", passenger, weekday, direction, driver_b)
                else:
                    eligible = _is_eligible(passenger, target, members, day_a, schoolbound, tolerance)
                    free_seat = len(target.passengers) < _capacity(members[driver_b], day_a, schoolbound)
                    if eligible and free_seat:
                        parties_a[driver_a].passengers.remove(passenger)
                        target.passengers.append(passenger)
                        unified.add((day_a, direction, passenger))
                        unified.add((day_b, direction, passenger))
                        logger.info("[ab-unify] moved %s from %s onto %s's week-A party (%s/%s)",
                                    passenger, driver_a, driver_b, weekday, direction)
                        continue
                    logger.debug("[ab-unify] %s on %s/%s: option 1 (%s -> %s) blocked "
                                 "(eligible=%s, free_seat=%s)",
                                 passenger, weekday, direction, driver_a, driver_b, eligible, free_seat)

                # Option 2: move the passenger onto driver_a's party in week B.
                target = parties_b.get(driver_a)
                if target is None:
                    logger.debug("[ab-unify] %s on %s/%s: %s (week-A driver) doesn't drive week B - "
                                 "no option 2", passenger, weekday, direction, driver_a)
                    continue
                eligible = _is_eligible(passenger, target, members, day_b, schoolbound, tolerance)
                free_seat = len(target.passengers) < _capacity(members[driver_a], day_b, schoolbound)
                if eligible and free_seat:
                    parties_b[driver_b].passengers.remove(passenger)
                    target.passengers.append(passenger)
                    unified.add((day_a, direction, passenger))
                    unified.add((day_b, direction, passenger))
                    logger.info("[ab-unify] moved %s from %s onto %s's week-B party (%s/%s)",
                                passenger, driver_b, driver_a, weekday, direction)
                else:
                    logger.debug("[ab-unify] %s on %s/%s: option 2 (%s -> %s) blocked "
                                 "(eligible=%s, free_seat=%s) - staying split (%s/%s)",
                                 passenger, weekday, direction, driver_b, driver_a, eligible, free_seat,
                                 driver_a, driver_b)

    return unified


def _balance_even_distribution(parties: List[Party], members: Dict[str, Member],
                                day_num: int, schoolbound: bool, tolerance: int,
                                protected: set = frozenset()) -> bool:
    """
    Among placements that are exactly as good for a passenger (same
    time-distance to more than one eligible party), prefer the
    less-loaded party, to avoid some parties sitting empty while others
    carry several passengers (concern 3, lowest priority - only breaks
    genuine ties, never overrides a strictly closer-time placement).

    `protected` holds passenger initials that _unify_week_ab just placed with
    a matching A/B driver (concern 2 outranks concern 3) - they're skipped as
    movers so this pass can't undo that work; every time one would otherwise
    have been picked, it's logged so a real conflict between the two goals is
    visible rather than silently overridden.

    Returns whether any passenger was actually moved, so the caller (see
    optimize_passenger_placement) can tell whether re-running _unify_week_ab
    is worth it - a move here can free up capacity elsewhere that turns a
    previously-blocked A/B unification into a feasible one.
    """
    any_moved = False
    changed = True
    while changed:
        changed = False
        for light in sorted(parties, key=lambda p: len(p.passengers)):
            capacity_light = _capacity(members[light.driver], day_num, schoolbound)
            if len(light.passengers) >= capacity_light:
                continue
            for heavy in sorted(parties, key=lambda p: -len(p.passengers)):
                if heavy is light or len(heavy.passengers) - len(light.passengers) < 2:
                    continue
                tied = [
                    passenger for passenger in heavy.passengers
                    if _is_eligible(passenger, light, members, day_num, schoolbound, tolerance)
                    and _distance(passenger, light, members, day_num, schoolbound)
                        == _distance(passenger, heavy, members, day_num, schoolbound)
                ]
                mover = next((passenger for passenger in tied if passenger not in protected), None)
                if mover is None and tied:
                    logger.info("[even-distribution] day %s/%s: skipped moving %s from %s to %s "
                                "(protected by ab-unify) - goal #2 outranks goal #3 here",
                                day_num, "schoolbound" if schoolbound else "homebound",
                                tied, heavy.driver, light.driver)
                if mover:
                    heavy.passengers.remove(mover)
                    light.passengers.append(mover)
                    changed = True
                    any_moved = True
                    break
            if changed:
                break

    return any_moved


def _tie_candidates(passenger: str, source: Party, parties: Dict[str, Party], members: Dict[str, Member],
                     day_num: int, schoolbound: bool, tolerance: int) -> set:
    """Drivers whose party would be a legitimate even-distribution
    destination for `passenger`, currently with `source`'s driver: enough of
    a load difference to matter (>=2), an equally close fit, eligible, and
    with room."""
    candidates = set()
    for party in parties.values():
        if party is source or len(source.passengers) - len(party.passengers) < 2:
            continue
        if not _is_eligible(passenger, party, members, day_num, schoolbound, tolerance):
            continue
        if _distance(passenger, party, members, day_num, schoolbound) != \
                _distance(passenger, source, members, day_num, schoolbound):
            continue
        if len(party.passengers) >= _capacity(members[party.driver], day_num, schoolbound):
            continue
        candidates.add(party.driver)
    return candidates


def _is_feasible_target(passenger: str, driver: str, parties: Dict[str, Party], members: Dict[str, Member],
                         day_num: int, schoolbound: bool, tolerance: int) -> bool:
    """Whether `driver`'s party this week could take `passenger` right now -
    the weaker check used for the *other* week of a synced A/B move, where a
    genuine load-balancing tie isn't required, just that the pairing stays
    valid there too."""
    party = parties.get(driver)
    if party is None:
        return False
    if not _is_eligible(passenger, party, members, day_num, schoolbound, tolerance):
        return False
    return len(party.passengers) < _capacity(members[driver], day_num, schoolbound)


def _balance_even_distribution_synced(parties_by_day: Dict[int, Dict[str, List[Party]]],
                                       members: Dict[str, Member], tolerance: int, unified: set) -> bool:
    """
    Rebalances load (concern 3) for passengers _unify_week_ab just matched
    onto the same driver both weeks, without breaking that match: instead of
    leaving them untouched (see _balance_even_distribution's `protected`),
    move the *pair* - same passenger, same new driver, both weeks at once.
    A destination only has to be a genuine load-balancing tie in one of the
    two weeks; the other week just has to stay a valid (eligible, has room)
    placement, since the point here is carrying the passenger along, not a
    second independent rebalancing decision.
    """
    any_moved = False

    for weekday in range(5):
        day_a, day_b = weekday, weekday + 5
        for direction in DIRECTIONS:
            schoolbound = direction == "schoolbound"
            parties_a = {p.driver: p for p in parties_by_day[day_a][direction]}
            parties_b = {p.driver: p for p in parties_by_day[day_b][direction]}

            matched_here = sorted({
                passenger for (d, dirn, passenger) in unified
                if dirn == direction and d in (day_a, day_b)
            })

            for passenger in matched_here:
                driver_a = next((p.driver for p in parties_a.values() if passenger in p.passengers), None)
                driver_b = next((p.driver for p in parties_b.values() if passenger in p.passengers), None)
                if driver_a is None or driver_b is None or driver_a != driver_b:
                    continue  # not actually unified here - leave to the per-week pass

                source_a, source_b = parties_a[driver_a], parties_b[driver_b]
                candidates = (
                    _tie_candidates(passenger, source_a, parties_a, members, day_a, schoolbound, tolerance)
                    | _tie_candidates(passenger, source_b, parties_b, members, day_b, schoolbound, tolerance)
                )

                target = next(
                    (driver for driver in sorted(candidates)
                     if _is_feasible_target(passenger, driver, parties_a, members, day_a, schoolbound, tolerance)
                     and _is_feasible_target(passenger, driver, parties_b, members, day_b, schoolbound, tolerance)),
                    None
                )
                if target is None:
                    continue

                source_a.passengers.remove(passenger)
                parties_a[target].passengers.append(passenger)
                source_b.passengers.remove(passenger)
                parties_b[target].passengers.append(passenger)
                any_moved = True
                logger.info("[even-distribution] moved matched pair %s from %s to %s on both weeks (%s/%s) "
                            "to balance load without splitting them (goal #2 stays intact)",
                            passenger, driver_a, target, weekday, direction)

    return any_moved


def _recompute_party_time(party: Party, members: Dict[str, Member],
                           day_num: int, schoolbound: bool) -> None:
    """Mirrors SolverService._extract_parties: the meeting time is the
    earliest (schoolbound) / latest (homebound) of the driver's own time and
    its current passengers' own times."""
    times = [party.original_driver_time] + [
        _desired_time(members[p], day_num, schoolbound) for p in party.passengers
    ]
    party.time = min(times) if schoolbound else max(times)


#  _unify_week_ab and _balance_even_distribution can each unblock the other
#  (freeing a seat lets a unification through; unifying changes who's tied
#  for a balance move) - _MAX_UNIFY_BALANCE_ROUNDS bounds the back-and-forth
#  to a small constant. In practice one or two rounds settle it; the cap just
#  guards against pathological oscillation on unusual inputs.
_MAX_UNIFY_BALANCE_ROUNDS = 5


def optimize_passenger_placement(members: Dict[str, Member],
                                  parties_by_day: Dict[int, Dict[str, List[Party]]],
                                  tolerance: int) -> None:
    """
    Improves passenger-to-party placement after the solver has decided who
    drives, in priority order: closest-time placement, then week A/B
    similarity, then even distribution as a tie-break. Mutates
    `parties_by_day` in place; never changes who drives.
    """
    for day_num in range(10):
        for direction in DIRECTIONS:
            schoolbound = direction == "schoolbound"
            _rebalance_day_direction(parties_by_day[day_num][direction], members, day_num, schoolbound, tolerance)

    # Run week A/B unification and even-distribution together, to a fixed
    # point: a balance move can free up the exact seat a unification needed
    # (see plan_postprocessor's module docstring for the motivating example),
    # so a single unify-then-balance pass can leave easy unifications on the
    # table purely because of pass ordering, not because they're infeasible.
    for round_num in range(_MAX_UNIFY_BALANCE_ROUNDS):
        unified = _unify_week_ab(parties_by_day, members, tolerance)

        # Matched passengers get balanced as a synced pair first (both weeks
        # move together, so goal #3 never splits a goal #2 match); only
        # non-matched passengers are left for the plain per-week pass below.
        any_balance_change = _balance_even_distribution_synced(parties_by_day, members, tolerance, unified)

        for day_num in range(10):
            for direction in DIRECTIONS:
                schoolbound = direction == "schoolbound"
                protected = {p for (d, dirn, p) in unified if d == day_num and dirn == direction}
                changed = _balance_even_distribution(parties_by_day[day_num][direction], members, day_num,
                                                       schoolbound, tolerance, protected)
                any_balance_change = any_balance_change or changed

        if not any_balance_change:
            break
        logger.info("[optimize] round %s: even-distribution moved passengers, re-running ab-unify", round_num + 1)

    for day_num in range(10):
        for direction in DIRECTIONS:
            schoolbound = direction == "schoolbound"
            for party in parties_by_day[day_num][direction]:
                _recompute_party_time(party, members, day_num, schoolbound)
