"""
Unit tests for the summary-tab "plan quality" metrics (see plan_quality.py).
Pure unit tests against hand-built Member/Party/DayPlan fixtures.
"""
import sys
from pathlib import Path

backend_src = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(backend_src))

from models import DayOfWeekABCombo, DayPlan, Member, Party, Timetable  # type: ignore # noqa: E402
from plan_quality import compute_quality_metrics  # type: ignore # noqa: E402

TOLERANCE = 30


def _member(initials, seats=4, is_part_time=False, drive_count=0, max_drives=4, first_name=None):
    m = Member(first_name=first_name or initials, last_name=initials, initials=initials, number_of_seats=seats,
               is_part_time=is_part_time)
    m.drive_count = drive_count
    m.max_drives = max_drives
    return m


def _set_time(member, day_num, start=None, end=None):
    member.timetable[day_num] = Timetable(
        member_initials=member.initials, day_number=day_num,
        start_time=start, end_time=end,
        scheduled_start_time=start, scheduled_end_time=end,
    )


def _party(driver, time, passengers, schoolbound=True, day_of_week='MONDAY', is_week_a=True):
    return Party(
        day_of_week_ab_combo=DayOfWeekABCombo(day_of_week=day_of_week, is_week_a=is_week_a, unique_number=1),
        driver=driver, time=time,
        passengers=list(passengers), is_designated_driver=False,
        drives_despite_custom_prefs=False, schoolbound=schoolbound,
        original_driver_time=time,
    )


def _empty_day_plans():
    return {day_key: DayPlan(day_of_week_ab_combo=None, parties=[]) for day_key in range(1, 11)}


def test_flexibility_counts_ride_as_covered_when_another_driver_has_room():
    d1, d2, p = _member('D1'), _member('D2'), _member('P')
    _set_time(d1, 0, start=745)
    _set_time(d2, 0, start=750)
    _set_time(p, 0, start=745)
    members = {'D1': d1, 'D2': d2, 'P': p}

    day_plans = _empty_day_plans()
    day_plans[1].parties = [_party('D1', 745, ['P']), _party('D2', 750, [])]

    metrics = compute_quality_metrics(members, day_plans, TOLERANCE)

    assert metrics['flexibility']['value'] == 100
    assert metrics['flexibility']['coveredRides'] == 1
    assert metrics['flexibility']['totalRidesWithPassengers'] == 1


def test_flexibility_counts_ride_as_uncovered_when_no_one_has_room():
    d1, d2, p = _member('D1'), _member('D2', seats=1), _member('P')
    _set_time(d1, 0, start=745)
    _set_time(d2, 0, start=745)
    _set_time(p, 0, start=745)
    members = {'D1': d1, 'D2': d2, 'P': p}

    day_plans = _empty_day_plans()
    # D2 has 1 seat total -> 0 passenger capacity, so P has nowhere to go.
    day_plans[1].parties = [_party('D1', 745, ['P']), _party('D2', 745, [])]

    metrics = compute_quality_metrics(members, day_plans, TOLERANCE)

    assert metrics['flexibility']['value'] == 0
    assert metrics['flexibility']['coveredRides'] == 0


def test_flexibility_ignores_rides_with_no_passengers():
    d1 = _member('D1')
    _set_time(d1, 0, start=745)
    members = {'D1': d1}

    day_plans = _empty_day_plans()
    day_plans[1].parties = [_party('D1', 745, [])]

    metrics = compute_quality_metrics(members, day_plans, TOLERANCE)

    assert metrics['flexibility']['totalRidesWithPassengers'] == 0
    assert metrics['flexibility']['value'] == 100


def test_packed_parties_only_flags_full_five_seaters():
    d1, d2 = _member('D1', seats=5), _member('D2', seats=4)
    p1, p2, p3, p4 = (_member(f'P{i}') for i in range(1, 5))
    members = {'D1': d1, 'D2': d2, 'P1': p1, 'P2': p2, 'P3': p3, 'P4': p4}
    for member in members.values():
        _set_time(member, 0, start=745)

    day_plans = _empty_day_plans()
    day_plans[1].parties = [
        _party('D1', 745, ['P1', 'P2', 'P3', 'P4']),  # 5-seater, full (4 passengers)
        _party('D2', 745, ['P1', 'P2', 'P3']),  # 4-seater, full but not a 5-seater
    ]

    metrics = compute_quality_metrics(members, day_plans, TOLERANCE)

    assert metrics['packedParties']['value'] == 100
    assert metrics['packedParties']['packedCount'] == 1
    assert metrics['packedParties']['totalFiveSeaterRides'] == 1
    assert len(metrics['packedParties']['parties']) == 1
    packed_party = metrics['packedParties']['parties'][0]
    assert packed_party['dayOfWeek'] == 'MONDAY'
    assert packed_party['isWeekA'] is True
    assert packed_party['time'] == 745
    assert packed_party['driver'] == {'initials': 'D1', 'firstName': 'D1'}
    assert packed_party['passengers'] == [
        {'initials': 'P1', 'firstName': 'P1'}, {'initials': 'P2', 'firstName': 'P2'},
        {'initials': 'P3', 'firstName': 'P3'}, {'initials': 'P4', 'firstName': 'P4'},
    ]


def test_packed_parties_value_is_a_percentage_of_five_seater_rides():
    d1, d2 = _member('D1', seats=5), _member('D2', seats=5)
    p1, p2, p3, p4 = (_member(f'P{i}') for i in range(1, 5))
    members = {'D1': d1, 'D2': d2, 'P1': p1, 'P2': p2, 'P3': p3, 'P4': p4}
    for member in members.values():
        _set_time(member, 0, start=745)

    day_plans = _empty_day_plans()
    day_plans[1].parties = [
        _party('D1', 745, ['P1', 'P2', 'P3', 'P4']),  # 5-seater, full
        _party('D2', 745, ['P1']),  # 5-seater, not full
    ]

    metrics = compute_quality_metrics(members, day_plans, TOLERANCE)

    assert metrics['packedParties']['value'] == 50
    assert metrics['packedParties']['packedCount'] == 1
    assert metrics['packedParties']['totalFiveSeaterRides'] == 2


def test_ab_driver_mismatch_flags_genuinely_different_pattern():
    # M drives Monday-A but Tuesday-B instead - same drive count (1) both
    # weeks, but a genuinely different day, not an unavoidable odd-split swing.
    m, other = _member('M', first_name='Michel'), _member('OTHER')
    members = {'M': m, 'OTHER': other}

    day_plans = _empty_day_plans()
    day_plans[1].parties = [_party('M', 745, [])]
    day_plans[7].parties = [_party('M', 745, [])]

    metrics = compute_quality_metrics(members, day_plans, TOLERANCE)

    assert metrics['abDriverMismatch']['mismatchedCount'] == 1
    assert metrics['abDriverMismatch']['totalMembers'] == 2
    assert metrics['abDriverMismatch']['value'] == 50
    assert metrics['abDriverMismatch']['members'] == [
        {'initials': 'M', 'firstName': 'Michel', 'weekdaysA': [0], 'weekdaysB': [1]}
    ]


def test_ab_driver_mismatch_tolerates_one_day_swing_from_odd_total():
    # M drives Monday+Tuesday in week A, and Monday+Tuesday+Thursday in week
    # B - the extra Thursday is an unavoidable odd-total swing (B is a
    # strict superset of A by exactly one day), not a "different pattern".
    m = _member('M')
    members = {'M': m}

    day_plans = _empty_day_plans()
    day_plans[1].parties = [_party('M', 745, [])]
    day_plans[2].parties = [_party('M', 745, [])]
    day_plans[6].parties = [_party('M', 745, [])]
    day_plans[7].parties = [_party('M', 745, [])]
    day_plans[9].parties = [_party('M', 745, [])]

    metrics = compute_quality_metrics(members, day_plans, TOLERANCE)

    assert metrics['abDriverMismatch']['mismatchedCount'] == 0
    assert metrics['abDriverMismatch']['value'] == 0


def test_ab_driver_mismatch_is_zero_when_pattern_matches():
    m = _member('M')
    members = {'M': m}

    day_plans = _empty_day_plans()
    day_plans[1].parties = [_party('M', 745, [])]
    day_plans[6].parties = [_party('M', 745, [])]

    metrics = compute_quality_metrics(members, day_plans, TOLERANCE)

    assert metrics['abDriverMismatch']['value'] == 0
    assert metrics['abDriverMismatch']['mismatchedCount'] == 0


def test_passenger_ab_stability_counts_same_driver_both_weeks_as_matched():
    d1, d2, p = _member('D1'), _member('D2'), _member('P')
    members = {'D1': d1, 'D2': d2, 'P': p}

    day_plans = _empty_day_plans()
    day_plans[1].parties = [_party('D1', 745, ['P'])]
    day_plans[6].parties = [_party('D1', 745, ['P'])]

    metrics = compute_quality_metrics(members, day_plans, TOLERANCE)

    assert metrics['passengerAbStability']['value'] == 100
    assert metrics['passengerAbStability']['matchedCount'] == 1
    assert metrics['passengerAbStability']['totalComparableRides'] == 1
    assert metrics['passengerAbStability']['mismatches'] == []


def test_passenger_ab_stability_flags_different_driver_between_weeks():
    d1, d2, p = _member('D1'), _member('D2'), _member('P')
    members = {'D1': d1, 'D2': d2, 'P': p}

    day_plans = _empty_day_plans()
    day_plans[1].parties = [_party('D1', 745, ['P'])]
    day_plans[6].parties = [_party('D2', 745, ['P'])]

    metrics = compute_quality_metrics(members, day_plans, TOLERANCE)

    assert metrics['passengerAbStability']['value'] == 0
    assert metrics['passengerAbStability']['matchedCount'] == 0
    assert metrics['passengerAbStability']['totalComparableRides'] == 1
    assert metrics['passengerAbStability']['mismatches'] == [
        {'initials': 'P', 'weekday': 0, 'schoolbound': True, 'driverA': 'D1', 'driverB': 'D2'}
    ]


def test_passenger_ab_stability_ignores_passenger_absent_one_week():
    d1, p = _member('D1'), _member('P')
    members = {'D1': d1, 'P': p}

    day_plans = _empty_day_plans()
    day_plans[1].parties = [_party('D1', 745, ['P'])]
    # Monday-B: P doesn't travel at all.

    metrics = compute_quality_metrics(members, day_plans, TOLERANCE)

    assert metrics['passengerAbStability']['totalComparableRides'] == 0
    assert metrics['passengerAbStability']['value'] == 100
