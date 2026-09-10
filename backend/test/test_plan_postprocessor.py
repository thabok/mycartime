"""
Unit tests for the passenger-placement post-processing pass (see
plan_postprocessor.py). Pure unit tests against hand-built Member/Party
fixtures - no solver involved, since the whole point of this module is to
operate on whatever parties the solver (or a test) already decided.
"""
import sys
from pathlib import Path

backend_src = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(backend_src))

from models import CustomDay, Member, Party, Timetable  # type: ignore # noqa: E402
from plan_postprocessor import (_is_eligible, optimize_passenger_placement,  # type: ignore # noqa: E402
                                 _rebalance_day_direction, _unify_week_ab,
                                 _balance_even_distribution, _balance_even_distribution_synced)

DAY = 0
TOLERANCE = 30


def _member(initials, seats=4, custom_days=None):
    return Member(
        first_name=initials, last_name=initials, initials=initials,
        number_of_seats=seats, custom_days=custom_days or {},
    )


def _set_time(member, day_num, start=None, end=None):
    member.timetable[day_num] = Timetable(
        member_initials=member.initials, day_number=day_num,
        start_time=start, end_time=end,
        scheduled_start_time=start, scheduled_end_time=end,
    )


def _party(driver, time, passengers, day_num=DAY, schoolbound=True):
    return Party(
        day_of_week_ab_combo=None, driver=driver, time=time,
        passengers=list(passengers), is_designated_driver=False,
        drives_despite_custom_prefs=False, schoolbound=schoolbound,
        original_driver_time=time,
    )


def test_passenger_moves_to_closer_time_party_when_capacity_allows():
    # D1 drives at 7:45, D2 at 7:55. P wants 7:45 but got placed with D2.
    d1, d2, p = _member('D1'), _member('D2'), _member('P')
    _set_time(d1, DAY, start=745)
    _set_time(d2, DAY, start=755)
    _set_time(p, DAY, start=745)
    members = {'D1': d1, 'D2': d2, 'P': p}

    party_d1 = _party('D1', 745, [])
    party_d2 = _party('D2', 755, ['P'])
    parties = [party_d1, party_d2]

    _rebalance_day_direction(parties, members, DAY, True, TOLERANCE)

    assert party_d1.passengers == ['P']
    assert party_d2.passengers == []


def test_passenger_stays_put_when_current_party_is_already_closest():
    d1, d2, p = _member('D1'), _member('D2'), _member('P')
    _set_time(d1, DAY, start=745)
    _set_time(d2, DAY, start=755)
    _set_time(p, DAY, start=755)
    members = {'D1': d1, 'D2': d2, 'P': p}

    party_d1 = _party('D1', 745, [])
    party_d2 = _party('D2', 755, ['P'])
    parties = [party_d1, party_d2]

    _rebalance_day_direction(parties, members, DAY, True, TOLERANCE)

    assert party_d1.passengers == []
    assert party_d2.passengers == ['P']


def test_full_capacity_party_only_displaced_by_a_strictly_closer_passenger():
    # D1 (2 seats) already carries P1 (7:50, further from 7:45 than P2).
    # P2 (7:45) proposes to D1 and should bump P1 out; P1 then falls back to D2.
    d1, d2 = _member('D1', seats=2), _member('D2', seats=4)
    p1, p2 = _member('P1'), _member('P2')
    _set_time(d1, DAY, start=745)
    _set_time(d2, DAY, start=800)
    _set_time(p1, DAY, start=750)
    _set_time(p2, DAY, start=745)
    members = {'D1': d1, 'D2': d2, 'P1': p1, 'P2': p2}

    party_d1 = _party('D1', 745, ['P1'])
    party_d2 = _party('D2', 800, ['P2'])
    parties = [party_d1, party_d2]

    _rebalance_day_direction(parties, members, DAY, True, TOLERANCE)

    assert party_d1.passengers == ['P2']
    assert party_d2.passengers == ['P1']


def test_solo_pm_driver_never_becomes_eligible():
    driver = _member('D1', custom_days={DAY: CustomDay(needs_car=True, solo_pm=True)})
    passenger = _member('P')
    _set_time(driver, DAY, end=1600)
    _set_time(passenger, DAY, end=1600)
    members = {'D1': driver, 'P': passenger}

    party = _party('D1', 1600, [], schoolbound=False)
    assert not _is_eligible('P', party, members, DAY, False, TOLERANCE)


def test_no_waiting_afternoon_driver_blocks_passenger_who_finishes_later():
    # Driver has noWaitingAfternoon and must leave at exactly 1500. A
    # passenger finishing at 1515 would make them wait, so they must not be
    # considered eligible even though 15 minutes is within general tolerance.
    driver = _member('D1', custom_days={DAY: CustomDay(no_waiting_afternoon=True)})
    passenger = _member('P')
    _set_time(driver, DAY, end=1500)
    _set_time(passenger, DAY, end=1515)
    members = {'D1': driver, 'P': passenger}

    party = _party('D1', 1500, [], schoolbound=False)
    assert not _is_eligible('P', party, members, DAY, False, TOLERANCE)


def test_week_ab_unification_moves_passenger_onto_shared_driver():
    # Passenger rides with D1 on Monday-A and D2 on Monday-B, but D1 also
    # drives Monday-B and could eligibly carry them there.
    d1, d2, p = _member('D1'), _member('D2'), _member('P')
    for day in (0, 5):
        _set_time(d1, day, start=745)
        _set_time(d2, day, start=750)
        _set_time(p, day, start=745)
    members = {'D1': d1, 'D2': d2, 'P': p}

    parties_by_day = {
        0: {'schoolbound': [_party('D1', 745, ['P'], day_num=0), _party('D2', 750, [], day_num=0)], 'homebound': []},
        5: {'schoolbound': [_party('D1', 745, [], day_num=5), _party('D2', 750, ['P'], day_num=5)], 'homebound': []},
    }
    for d in range(1, 5):
        parties_by_day[d] = {'schoolbound': [], 'homebound': []}
    for d in range(6, 10):
        parties_by_day[d] = {'schoolbound': [], 'homebound': []}

    _unify_week_ab(parties_by_day, members, TOLERANCE)

    # Whichever driver they end up unified onto, it must be the *same* one
    # in both weeks, and no one else was displaced to make room.
    driver_a = next(party.driver for party in parties_by_day[0]['schoolbound'] if 'P' in party.passengers)
    driver_b = next(party.driver for party in parties_by_day[5]['schoolbound'] if 'P' in party.passengers)
    assert driver_a == driver_b
    for party in parties_by_day[0]['schoolbound'] + parties_by_day[5]['schoolbound']:
        assert party.passengers in ([], ['P'])


def test_unify_week_ab_returns_the_set_of_unified_entries():
    # Same fixture as above, but checking the return value directly: this is
    # what optimize_passenger_placement feeds to _balance_even_distribution
    # so it can't undo the unification (goal #2 outranks goal #3).
    d1, d2, p = _member('D1'), _member('D2'), _member('P')
    for day in (0, 5):
        _set_time(d1, day, start=745)
        _set_time(d2, day, start=750)
        _set_time(p, day, start=745)
    members = {'D1': d1, 'D2': d2, 'P': p}

    parties_by_day = {
        0: {'schoolbound': [_party('D1', 745, ['P'], day_num=0), _party('D2', 750, [], day_num=0)], 'homebound': []},
        5: {'schoolbound': [_party('D1', 745, [], day_num=5), _party('D2', 750, ['P'], day_num=5)], 'homebound': []},
    }
    for d in range(1, 5):
        parties_by_day[d] = {'schoolbound': [], 'homebound': []}
    for d in range(6, 10):
        parties_by_day[d] = {'schoolbound': [], 'homebound': []}

    unified = _unify_week_ab(parties_by_day, members, TOLERANCE)

    assert (0, 'schoolbound', 'P') in unified
    assert (5, 'schoolbound', 'P') in unified


def test_even_distribution_never_moves_a_protected_passenger():
    # P is protected (already unified across A/B by _unify_week_ab); X is an
    # ordinary passenger equally good fit for the light party. Both are tied
    # candidates to balance load, but only X may be picked - moving P would
    # silently undo the A/B unification (goal #2 outranks goal #3).
    d1, d2, p, x = _member('D1'), _member('D2'), _member('P'), _member('X')
    _set_time(d1, DAY, start=800)
    _set_time(d2, DAY, start=800)
    _set_time(p, DAY, start=800)
    _set_time(x, DAY, start=800)
    members = {'D1': d1, 'D2': d2, 'P': p, 'X': x}

    party_d1 = _party('D1', 800, ['P', 'X'])
    party_d2 = _party('D2', 800, [])
    parties = [party_d1, party_d2]

    _balance_even_distribution(parties, members, DAY, True, TOLERANCE, protected={'P'})

    assert 'P' in party_d1.passengers
    assert 'X' in party_d2.passengers


def test_synced_balance_moves_a_matched_pair_together():
    # P is unified onto D1 both weeks. D1 is heavy in week A (2 passengers
    # vs D2's 0 - a genuine tie-break opportunity) but only 1-vs-0 in week B
    # (not enough on its own). The synced pass should still move P to D2 in
    # *both* weeks at once, since D2 has room and is an equally good fit in
    # both, rather than leaving P split or skipping the rebalance entirely.
    d1, d2 = _member('D1', seats=4), _member('D2', seats=4)
    p, f = _member('P'), _member('F')
    _set_time(d1, 0, start=800)
    _set_time(d1, 5, start=800)
    _set_time(d2, 0, start=800)
    _set_time(d2, 5, start=800)
    _set_time(p, 0, start=800)
    _set_time(p, 5, start=800)
    _set_time(f, 0, start=800)
    members = {'D1': d1, 'D2': d2, 'P': p, 'F': f}

    party_d1_a = _party('D1', 800, ['P', 'F'], day_num=0)
    party_d2_a = _party('D2', 800, [], day_num=0)
    party_d1_b = _party('D1', 800, ['P'], day_num=5)
    party_d2_b = _party('D2', 800, [], day_num=5)

    parties_by_day = {
        0: {'schoolbound': [party_d1_a, party_d2_a], 'homebound': []},
        5: {'schoolbound': [party_d1_b, party_d2_b], 'homebound': []},
    }
    for d in list(range(1, 5)) + list(range(6, 10)):
        parties_by_day[d] = {'schoolbound': [], 'homebound': []}

    unified = {(0, 'schoolbound', 'P'), (5, 'schoolbound', 'P')}
    moved = _balance_even_distribution_synced(parties_by_day, members, TOLERANCE, unified)

    assert moved is True
    assert party_d1_a.passengers == ['F']
    assert party_d2_a.passengers == ['P']
    assert party_d1_b.passengers == []
    assert party_d2_b.passengers == ['P']


def test_synced_balance_leaves_pair_untouched_when_target_infeasible_one_week():
    # Same imbalance as above, but D2 doesn't drive week B at all, so moving
    # P there would split the A/B match - the synced pass must not do that.
    d1, d2 = _member('D1', seats=4), _member('D2', seats=4)
    p, f = _member('P'), _member('F')
    _set_time(d1, 0, start=800)
    _set_time(d1, 5, start=800)
    _set_time(d2, 0, start=800)
    _set_time(p, 0, start=800)
    _set_time(p, 5, start=800)
    _set_time(f, 0, start=800)
    members = {'D1': d1, 'D2': d2, 'P': p, 'F': f}

    party_d1_a = _party('D1', 800, ['P', 'F'], day_num=0)
    party_d2_a = _party('D2', 800, [], day_num=0)
    party_d1_b = _party('D1', 800, ['P'], day_num=5)

    parties_by_day = {
        0: {'schoolbound': [party_d1_a, party_d2_a], 'homebound': []},
        5: {'schoolbound': [party_d1_b], 'homebound': []},
    }
    for d in list(range(1, 5)) + list(range(6, 10)):
        parties_by_day[d] = {'schoolbound': [], 'homebound': []}

    unified = {(0, 'schoolbound', 'P'), (5, 'schoolbound', 'P')}
    moved = _balance_even_distribution_synced(parties_by_day, members, TOLERANCE, unified)

    assert moved is False
    assert party_d1_a.passengers == ['P', 'F']
    assert party_d1_b.passengers == ['P']


def test_even_distribution_only_breaks_genuine_ties():
    # Two parties equally close (5 min) to P; D1 already has 2 passengers,
    # D2 has none, so the tie should resolve toward D2.
    d1, d2, p1, p2, p = _member('D1', seats=4), _member('D2', seats=4), _member('P1'), _member('P2'), _member('P')
    _set_time(d1, DAY, start=740)
    _set_time(d2, DAY, start=750)
    _set_time(p1, DAY, start=740)
    _set_time(p2, DAY, start=740)
    _set_time(p, DAY, start=745)
    members = {'D1': d1, 'D2': d2, 'P1': p1, 'P2': p2, 'P': p}

    party_d1 = _party('D1', 740, ['P1', 'P2', 'P'])
    party_d2 = _party('D2', 750, [])
    parties = [party_d1, party_d2]

    _balance_even_distribution(parties, members, DAY, True, TOLERANCE)

    assert sorted(party_d1.passengers) == ['P1', 'P2']
    assert party_d2.passengers == ['P']


def test_optimize_passenger_placement_recomputes_party_time():
    # Party time should reflect whoever ends up in it after reshuffling, not
    # a stale value from before the move.
    d1, d2, p = _member('D1'), _member('D2'), _member('P')
    _set_time(d1, DAY, start=745)
    _set_time(d2, DAY, start=755)
    _set_time(p, DAY, start=745)
    members = {'D1': d1, 'D2': d2, 'P': p}

    party_d1 = _party('D1', 745, [])
    party_d2 = _party('D2', 755, ['P'])
    parties_by_day = {DAY: {'schoolbound': [party_d1, party_d2], 'homebound': []}}
    for d in range(1, 10):
        parties_by_day[d] = {'schoolbound': [], 'homebound': []}

    optimize_passenger_placement(members, parties_by_day, TOLERANCE)

    assert party_d1.passengers == ['P']
    assert party_d1.time == 745
    assert party_d2.passengers == []
    assert party_d2.time == 755


def test_optimize_passenger_placement_unifies_ab_after_balance_frees_a_seat():
    # Regression test for a case that a single unify-then-balance pass would
    # miss entirely: P rides with D1 in week A, and with D2 in week B, but
    # D1's own week-B party is already full (Y1+Y2, capacity 2). A single
    # ab-unify attempt is correctly blocked. But Y1 and Y2 are equally close
    # to D1 and D3, so the even-distribution pass moves one of them (Y1) to
    # D3 to balance load, freeing exactly the seat P needed - a second
    # ab-unify round should then unify P onto D1 in both weeks.
    d1, d2, d3 = _member('D1', seats=3), _member('D2', seats=4), _member('D3', seats=4)
    p, y1, y2 = _member('P'), _member('Y1'), _member('Y2')

    for day in (0, 5):
        _set_time(p, day, start=805)
    _set_time(y1, 5, start=800)
    _set_time(y2, 5, start=800)
    members = {'D1': d1, 'D2': d2, 'D3': d3, 'P': p, 'Y1': y1, 'Y2': y2}

    party_d1_a = _party('D1', 800, ['P'], day_num=0)

    party_d1_b = _party('D1', 800, ['Y1', 'Y2'], day_num=5)
    party_d2_b = _party('D2', 805, ['P'], day_num=5)
    party_d3_b = _party('D3', 800, [], day_num=5)

    parties_by_day = {
        0: {'schoolbound': [party_d1_a], 'homebound': []},
        5: {'schoolbound': [party_d1_b, party_d2_b, party_d3_b], 'homebound': []},
    }
    for d in range(1, 5):
        parties_by_day[d] = {'schoolbound': [], 'homebound': []}
    for d in range(6, 10):
        parties_by_day[d] = {'schoolbound': [], 'homebound': []}

    optimize_passenger_placement(members, parties_by_day, TOLERANCE)

    assert party_d1_a.passengers == ['P']
    assert sorted(party_d1_b.passengers) == ['P', 'Y2']
    assert party_d2_b.passengers == []
    assert party_d3_b.passengers == ['Y1']
