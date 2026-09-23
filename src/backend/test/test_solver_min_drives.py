"""
Unit tests for the CP-SAT solver's max_drives *floor*: a member must drive at
least their quota (MAX_DRIVES_FULLTIME/PARTTIME), not just stay under it, so
that under-used members get extra driver parties rather than free-riding
below quota. See solver_service.py's `min_drives` constraint.
"""
import sys
from pathlib import Path

backend_src = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(backend_src))

import config  # noqa: E402
from models import Member, Timetable  # type: ignore # noqa: E402
from solver_service import SolverService  # type: ignore # noqa: E402


def _member(initials, seats=4, is_part_time=False):
    return Member(
        first_name=initials, last_name=initials, initials=initials,
        number_of_seats=seats, is_part_time=is_part_time,
    )


def _set_day(member, day_num, start=800, end=1400):
    member.timetable[day_num] = Timetable(
        member_initials=member.initials, day_number=day_num,
        start_time=start, end_time=end,
        scheduled_start_time=start, scheduled_end_time=end,
    )


def _present_every_day(member, days=range(10)):
    for day_num in days:
        _set_day(member, day_num)


def test_every_member_drives_at_least_their_quota_when_enough_days_present():
    # Three full-time members present all 10 days: each has a full week's worth
    # of days to draw from, well above MAX_DRIVES_FULLTIME (4), so the floor
    # must be hit exactly through solver-chosen extra driver assignments.
    members = [_member(i) for i in ('AA', 'BB', 'CC')]
    for m in members:
        _present_every_day(m)

    plan = SolverService().calculate_driving_plan(members)

    drive_counts = {m.initials: m.drive_count for m in members}
    for initials, count in drive_counts.items():
        assert count >= config.MAX_DRIVES_FULLTIME, (
            f"{initials} drove only {count} times, below quota "
            f"{config.MAX_DRIVES_FULLTIME}"
        )
    assert plan is not None


def test_part_time_member_hits_lower_quota_not_fulltime_one():
    # A part-time member mixed with full-time members should be held to the
    # lower part-time quota (3), not silently promoted to the full-time one.
    full_a, full_b = _member('AA'), _member('BB')
    part = _member('PT', is_part_time=True)
    members = [full_a, full_b, part]
    for m in members:
        _present_every_day(m)

    SolverService().calculate_driving_plan(members)

    assert part.drive_count >= config.MAX_DRIVES_PARTTIME
    for m in (full_a, full_b):
        assert m.drive_count >= config.MAX_DRIVES_FULLTIME


def test_floor_is_capped_by_available_days_not_infeasible():
    # A full-time member present only 2 of the 10 days can't possibly reach a
    # quota of 4; the floor must cap at their available days instead of making
    # the whole plan infeasible.
    scarce = _member('SC')
    _present_every_day(scarce, days=[0, 1])
    plenty = _member('PL')
    _present_every_day(plenty)
    members = [scarce, plenty]

    plan = SolverService().calculate_driving_plan(members)

    assert plan is not None
    assert scarce.drive_count <= 2
    assert plenty.drive_count >= config.MAX_DRIVES_FULLTIME
