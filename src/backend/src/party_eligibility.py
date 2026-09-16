"""
Shared "could this member ride with this party" rules, used both by
plan_postprocessor.py (deciding where to place a passenger) and
plan_quality.py (deciding whether a party has a backup driver if its own
driver called in sick). Mirrors SolverService._capacity/_can_carry
(solver_service.py) exactly, so post-hoc code never rates the plan by rules
looser or stricter than the ones the solver itself enforced.
"""
from typing import Dict

from models import Member, Party
from utils import times_within_tolerance


def capacity(member: Member, day_num: int, schoolbound: bool) -> int:
    """Passenger seats available if `member` drives this leg (0 when solo)."""
    solo = member.solo_am_on_day(day_num) if schoolbound else member.solo_pm_on_day(day_num)
    if solo:
        return 0
    return max(0, member.number_of_seats - 1)


def desired_time(member: Member, day_num: int, schoolbound: bool) -> int:
    """The member's own effective time for this leg (timetable or custom pref)."""
    return (member.get_effective_start_time(day_num) if schoolbound
            else member.get_effective_end_time(day_num))


def distance_minutes(passenger: str, party: Party, members: Dict[str, Member],
                      day_num: int, schoolbound: bool) -> int:
    """Minutes between a passenger's own desired time and the party's anchor
    (the driver's own time, not the possibly-drifted party.time), so the
    metric doesn't shift depending on who else is currently in the party."""
    p_time = desired_time(members[passenger], day_num, schoolbound)
    return abs(p_time - party.original_driver_time)


def is_eligible(passenger: str, party: Party, members: Dict[str, Member],
                day_num: int, schoolbound: bool, default_tolerance: int) -> bool:
    """Mirrors SolverService._can_carry, using each Party's driver anchor time."""
    if party.driver == passenger:
        return False
    driver_member = members[party.driver]
    if capacity(driver_member, day_num, schoolbound) <= 0:
        return False

    p_time = desired_time(members[passenger], day_num, schoolbound)
    d_time = party.original_driver_time
    tolerance = members[passenger].get_tolerance_for_direction(day_num, schoolbound, default_tolerance)
    if not times_within_tolerance(p_time, d_time, tolerance):
        return False

    if not schoolbound:
        # A noWaitingAfternoon driver must leave at their exact end time, so no
        # passenger who finishes later may join them, and vice versa.
        if driver_member.no_waiting_afternoon_on_day(day_num) and p_time > d_time:
            return False
        if members[passenger].no_waiting_afternoon_on_day(day_num) and d_time > p_time:
            return False
    return True
