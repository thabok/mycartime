"""
Unit tests for the CP-SAT solver's target-drive-count *floor*: a member must
drive at least their quota (DEFAULT_TARGET_DRIVE_COUNT_FULLTIME/PARTTIME, or
their own per-member override), not just stay under it, so that under-used
members get extra driver parties rather than free-riding below quota. See
solver_service.py's `min_drives` constraint.
"""
import sys
from pathlib import Path

backend_src = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(backend_src))

import config  # noqa: E402
from models import CustomDay, Member, Timetable  # type: ignore # noqa: E402
from solver_service import SolverService  # type: ignore # noqa: E402


def _member(shorthand, seats=4, is_part_time=False):
    return Member(
        first_name=shorthand, last_name=shorthand, shorthand=shorthand,
        number_of_seats=seats, is_part_time=is_part_time,
    )


def _set_day(member, day_num, start=800, end=1400):
    member.timetable[day_num] = Timetable(
        member_shorthand=member.shorthand, day_number=day_num,
        start_time=start, end_time=end,
        scheduled_start_time=start, scheduled_end_time=end,
    )


def _present_every_day(member, days=range(10)):
    for day_num in days:
        _set_day(member, day_num)


def test_every_member_drives_at_least_their_quota_when_enough_days_present():
    # Three full-time members present all 10 days: each has a full week's worth
    # of days to draw from, well above DEFAULT_TARGET_DRIVE_COUNT_FULLTIME (4),
    # so the floor must be hit exactly through solver-chosen extra driver
    # assignments.
    members = [_member(i) for i in ('AA', 'BB', 'CC')]
    for m in members:
        _present_every_day(m)

    plan = SolverService(alternating_weeks=True).calculate_driving_plan(members)

    drive_counts = {m.shorthand: m.drive_count for m in members}
    for shorthand, count in drive_counts.items():
        assert count >= config.DEFAULT_TARGET_DRIVE_COUNT_FULLTIME, (
            f"{shorthand} drove only {count} times, below quota "
            f"{config.DEFAULT_TARGET_DRIVE_COUNT_FULLTIME}"
        )
    assert plan is not None


def test_part_time_member_hits_lower_quota_not_fulltime_one():
    # A part-time member mixed with full-time members should be held to the
    # lower part-time quota (2), not silently promoted to the full-time one.
    full_a, full_b = _member('AA'), _member('BB')
    part = _member('PT', is_part_time=True)
    members = [full_a, full_b, part]
    for m in members:
        _present_every_day(m)

    SolverService(alternating_weeks=True).calculate_driving_plan(members)

    assert part.drive_count >= config.DEFAULT_TARGET_DRIVE_COUNT_PARTTIME
    for m in (full_a, full_b):
        assert m.drive_count >= config.DEFAULT_TARGET_DRIVE_COUNT_FULLTIME


def test_member_with_explicit_target_drive_count_overrides_type_default():
    # A full-time member with an explicit override should be held to their
    # own quota, not the type-based default.
    custom = _member('CU')
    custom.target_drive_count = 6
    typical = _member('TY')
    members = [custom, typical]
    for m in members:
        _present_every_day(m)

    SolverService(alternating_weeks=True).calculate_driving_plan(members)

    assert custom.drive_count >= 6
    assert typical.drive_count >= config.DEFAULT_TARGET_DRIVE_COUNT_FULLTIME


def test_floor_is_capped_by_available_days_not_infeasible():
    # A full-time member present only 2 of the 10 days can't possibly reach a
    # quota of 4; the floor must cap at their available days instead of making
    # the whole plan infeasible.
    scarce = _member('SC')
    _present_every_day(scarce, days=[0, 1])
    plenty = _member('PL')
    _present_every_day(plenty)
    members = [scarce, plenty]

    plan = SolverService(alternating_weeks=True).calculate_driving_plan(members)

    assert plan is not None
    assert scarce.drive_count <= 2
    assert plenty.drive_count >= config.DEFAULT_TARGET_DRIVE_COUNT_FULLTIME


def test_non_alternating_weeks_plans_five_days_with_flat_default_quota():
    # Without A/B weeks the cycle is Mon-Fri only, and full- and part-time
    # members share the same default target drive count.
    full_a, full_b = _member('AA'), _member('BB')
    part = _member('PT', is_part_time=True)
    members = [full_a, full_b, part]
    for m in members:
        _present_every_day(m, days=range(5))

    solver = SolverService(alternating_weeks=False, stop_after_no_improvement_seconds=5)
    plan = solver.calculate_driving_plan(members)

    assert sorted(plan.day_plans) == [1, 2, 3, 4, 5]
    assert plan.alternating_weeks is False
    for m in members:
        assert m.max_drives == config.DEFAULT_TARGET_DRIVE_COUNT_NON_ALTERNATING
        assert m.drive_count >= config.DEFAULT_TARGET_DRIVE_COUNT_NON_ALTERNATING
    assert 'abDriverMismatch' not in plan.quality_metrics
    assert 'weekABMismatches' not in solver.last_solve_stats['metrics']


def test_create_parties_for_underused_drivers_off_allows_under_quota():
    # BB needs a car every day (forced driver, quota raised so that alone
    # doesn't trigger overflow) and can carry AA the whole way, so AA riding
    # along every day is a fully sufficient plan - nothing else in the
    # objective rewards giving AA their own driver parties too. With the
    # floor disabled, AA must be allowed to stay at 0 instead of the solver
    # manufacturing parties just to fill AA's quota.
    forced_driver, rider = _member('BB'), _member('AA')
    forced_driver.target_drive_count = 10
    members = [forced_driver, rider]
    for m in members:
        _present_every_day(m)
    for day_num in range(10):
        forced_driver.custom_days[day_num] = CustomDay(needs_car=True)

    plan = SolverService(
        alternating_weeks=True,
        create_parties_for_underused_drivers=False,
        stop_after_no_improvement_seconds=5,
    ).calculate_driving_plan(members)

    assert plan is not None
    assert forced_driver.drive_count == 10
    assert rider.drive_count == 0


def test_quota_floor_never_forces_a_drivingskip_day():
    # SK has drivingSkip set on every day they're present, so they have zero
    # eligible days towards their quota. Even with the fairness floor on
    # (create_parties_for_underused_drivers defaults to True), the solver must
    # not manufacture a driver party for them on a skip day just to hit quota -
    # PL has ample seats to carry SK as a passenger every day instead.
    skip_member, plenty = _member('SK'), _member('PL')
    for m in (skip_member, plenty):
        _present_every_day(m)
    for day_num in range(10):
        skip_member.custom_days[day_num] = CustomDay(driving_skip=True)

    plan = SolverService(alternating_weeks=True, stop_after_no_improvement_seconds=5) \
        .calculate_driving_plan([skip_member, plenty])

    assert plan is not None
    assert skip_member.drive_count == 0


def test_non_alternating_weeks_ignores_week_b_custom_days():
    # Custom days keyed 5-9 are left over from alternating mode; they must not
    # trip validation (needsCar + drivingSkip together) in a 5-day cycle.
    member = _member('AA')
    other = _member('BB')
    for m in (member, other):
        _present_every_day(m, days=range(5))
    member.custom_days[7] = CustomDay(needs_car=True, driving_skip=True)

    plan = SolverService(alternating_weeks=False, stop_after_no_improvement_seconds=5) \
        .calculate_driving_plan([member, other])

    assert sorted(plan.day_plans) == [1, 2, 3, 4, 5]
