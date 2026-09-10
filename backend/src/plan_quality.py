"""
Computes the user-facing "plan quality" metrics shown on the driving plan's
summary tab. These are purely informational - read-only facts about a
finished DrivingPlan for the people using it, never inputs back into solving
or passenger placement (see plan_postprocessor.py for that).

Metric definitions (kept in sync with the frontend tooltips - see
PlanViewer.tsx):

- flexibility: of all rides that carry at least one passenger, what
  percentage could still happen - every passenger finding another eligible,
  non-full ride that same day/direction - if that ride's own driver
  suddenly called in sick. High is good.
- packedParties: percentage of all rides that are a 5-seater car at full
  capacity (driver + 4 passengers), where the 3 in the back have very little
  room. Non-5-seater rides count toward the total but can never be "packed".
  Low is good.
- abDriverMismatch: percentage of members whose driving weekdays (Mon-Fri)
  genuinely differ between week A and week B - tolerating the one-day swing
  an odd total drive count makes unavoidable (see _is_tolerated_swing). Low
  is good.
- passengerAbStability: of passengers who ride (as a passenger) on both the
  week-A and week-B instance of a given weekday+direction, what percentage
  ride with the same driver both weeks. Reflects how well
  plan_postprocessor.py's week A/B passenger-unification pass actually
  worked out for this plan. High is good.
"""
from typing import Dict, List

from models import DayPlan, Member, Party
from party_eligibility import capacity, is_eligible

DIRECTIONS = ("schoolbound", "homebound")


def _try_assign(passenger: str, eligible: Dict[str, List[str]], capacity_left: Dict[str, int],
                 assigned: Dict[str, List[str]], visited: set) -> bool:
    """Kuhn's algorithm augmenting-path step: can `passenger` be placed into
    one of their eligible drivers, bumping a worse-fit occupant to make room
    if every eligible driver is already full?"""
    for driver in eligible[passenger]:
        if driver in visited:
            continue
        visited.add(driver)
        occupants = assigned.setdefault(driver, [])
        if len(occupants) < capacity_left[driver]:
            occupants.append(passenger)
            return True
        for occupant in list(occupants):
            occupants.remove(occupant)
            if _try_assign(occupant, eligible, capacity_left, assigned, visited):
                occupants.append(passenger)
                return True
            occupants.append(occupant)
    return False


def _can_absorb_all(passengers: List[str], other_parties: List[Party], members: Dict[str, Member],
                     day_num: int, schoolbound: bool, tolerance: int) -> bool:
    """Whether every one of `passengers` could get a ride with one of
    `other_parties`'s drivers, respecting each driver's remaining spare
    capacity and the same eligibility rules the solver itself enforces."""
    capacity_left = {
        party.driver: capacity(members[party.driver], day_num, schoolbound) - len(party.passengers)
        for party in other_parties
    }
    eligible = {
        passenger: [party.driver for party in other_parties
                    if is_eligible(passenger, party, members, day_num, schoolbound, tolerance)]
        for passenger in passengers
    }
    assigned: Dict[str, List[str]] = {}
    for passenger in passengers:
        if not _try_assign(passenger, eligible, capacity_left, assigned, set()):
            return False
    return True


def _compute_flexibility(members: Dict[str, Member], day_plans: Dict[int, DayPlan], tolerance: int) -> dict:
    checked = 0
    covered = 0

    for day_key, day_plan in day_plans.items():
        day_num = day_key - 1  # day_plans is keyed 1-10; solo/custom-day lookups need the 0-9 day_num
        for schoolbound in (True, False):
            parties = [p for p in day_plan.parties if p.schoolbound == schoolbound]
            for party in parties:
                if not party.passengers:
                    continue
                checked += 1
                others = [p for p in parties if p.driver != party.driver]
                if _can_absorb_all(party.passengers, others, members, day_num, schoolbound, tolerance):
                    covered += 1

    percentage = round(100 * covered / checked) if checked else 100
    return {'value': percentage, 'coveredRides': covered, 'totalRidesWithPassengers': checked}


def _compute_packed_parties(day_plans: Dict[int, DayPlan], members: Dict[str, Member]) -> dict:
    packed = 0
    total_rides = 0
    packed_parties = []

    for day_plan in day_plans.values():
        for party in day_plan.parties:
            total_rides += 1
            driver_seats = members[party.driver].number_of_seats
            if driver_seats != 5:
                continue
            if len(party.passengers) == 4:
                packed += 1
                packed_parties.append({
                    'dayOfWeek': party.day_of_week_ab_combo.day_of_week,
                    'isWeekA': party.day_of_week_ab_combo.is_week_a,
                    'time': party.time,
                    'driver': {'initials': party.driver, 'firstName': members[party.driver].first_name},
                    'passengers': [
                        {'initials': initials, 'firstName': members[initials].first_name}
                        for initials in party.passengers
                    ],
                })

    percentage = round(100 * packed / total_rides) if total_rides else 0
    return {
        'value': percentage,
        'packedCount': packed,
        'totalRides': total_rides,
        'parties': packed_parties,
    }


def _is_tolerated_swing(weekdays_a: set, weekdays_b: set) -> bool:
    """
    Whether the difference between two weekday-sets is the kind of swing the
    solver's own objective already treats as unavoidable: a member with an
    odd total drive count can't split it evenly over two weeks, so one week
    having exactly one extra *on top of* the other week's days - not a
    different day, an additional one - is not a "different pattern", just an
    odd number landing somewhere. Mirrors SolverService._build_week_ab_similarity's
    `excess` term (a swing of one stays unpenalized; anything wider doesn't).
    """
    if weekdays_a == weekdays_b:
        return True
    if len(weekdays_a.symmetric_difference(weekdays_b)) != 1:
        return False
    return weekdays_a.issubset(weekdays_b) or weekdays_b.issubset(weekdays_a)


def _compute_ab_driver_mismatch(day_plans: Dict[int, DayPlan], members: Dict[str, Member]) -> dict:
    """
    Per member, which weekdays (Mon-Fri) they drive in week A vs week B. A
    member has a genuine mismatch if that pattern differs by more than the
    one-day swing an odd total drive count makes unavoidable (see
    _is_tolerated_swing) - e.g. driving Monday+Wednesday one week and
    Monday+Thursday the other is a real mismatch even though both weeks have
    2 drives, but Monday+Tuesday vs Monday+Tuesday+Thursday is just an
    unavoidable extra day and doesn't count.
    """
    weekdays_a: Dict[str, set] = {initials: set() for initials in members}
    weekdays_b: Dict[str, set] = {initials: set() for initials in members}

    for weekday in range(5):
        day_a, day_b = day_plans.get(weekday + 1), day_plans.get(weekday + 6)
        if day_a is not None:
            for party in day_a.parties:
                weekdays_a[party.driver].add(weekday)
        if day_b is not None:
            for party in day_b.parties:
                weekdays_b[party.driver].add(weekday)

    mismatched_members = [
        {
            'initials': initials,
            'firstName': members[initials].first_name,
            'weekdaysA': sorted(weekdays_a[initials]),
            'weekdaysB': sorted(weekdays_b[initials]),
        }
        for initials in sorted(members)
        if not _is_tolerated_swing(weekdays_a[initials], weekdays_b[initials])
    ]

    total_members = len(members)
    percentage = round(100 * len(mismatched_members) / total_members) if total_members else 0

    return {
        'value': percentage,
        'mismatchedCount': len(mismatched_members),
        'totalMembers': total_members,
        'members': mismatched_members,
    }


def _compute_passenger_ab_stability(day_plans: Dict[int, DayPlan]) -> dict:
    """
    For each passenger riding (as a passenger, not driver) on both the
    week-A and week-B instance of a given weekday+direction, do they ride
    with the same driver both weeks? Only passengers present both weeks on
    that leg are comparable - a passenger absent one week isn't a
    "different constellation", there's simply nothing to keep stable.
    """
    matched = 0
    total = 0
    mismatches = []

    for weekday in range(5):
        day_a, day_b = day_plans.get(weekday + 1), day_plans.get(weekday + 6)
        if day_a is None or day_b is None:
            continue

        for schoolbound in (True, False):
            driver_of_a = {
                passenger: party.driver
                for party in day_a.parties if party.schoolbound == schoolbound
                for passenger in party.passengers
            }
            driver_of_b = {
                passenger: party.driver
                for party in day_b.parties if party.schoolbound == schoolbound
                for passenger in party.passengers
            }

            for passenger in sorted(set(driver_of_a) & set(driver_of_b)):
                total += 1
                if driver_of_a[passenger] == driver_of_b[passenger]:
                    matched += 1
                else:
                    mismatches.append({
                        'initials': passenger,
                        'weekday': weekday,
                        'schoolbound': schoolbound,
                        'driverA': driver_of_a[passenger],
                        'driverB': driver_of_b[passenger],
                    })

    percentage = round(100 * matched / total) if total else 100
    return {
        'value': percentage,
        'matchedCount': matched,
        'totalComparableRides': total,
        'mismatches': mismatches,
    }


def compute_quality_metrics(members: Dict[str, Member], day_plans: Dict[int, DayPlan], tolerance: int) -> dict:
    """
    Builds the `qualityMetrics` block attached to DrivingPlan.to_dict().

    Args:
        members: all members, keyed by initials, with drive_count/max_drives
            already populated (see SolverService._apply_drive_counts).
        day_plans: the finished plan's day plans, keyed 1-10 (as in
            DrivingPlan.day_plans).
        tolerance: the tolerance (minutes) the plan was solved with.
    """
    return {
        'flexibility': _compute_flexibility(members, day_plans, tolerance),
        'packedParties': _compute_packed_parties(day_plans, members),
        'abDriverMismatch': _compute_ab_driver_mismatch(day_plans, members),
        'passengerAbStability': _compute_passenger_ab_stability(day_plans),
    }
