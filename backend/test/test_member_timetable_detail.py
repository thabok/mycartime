"""
Unit tests for the pure period-grouping/frequency logic behind the member
timetable detail endpoint. Pure unit tests, no WebUntis connection.
"""
import sys
from pathlib import Path

backend_src = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(backend_src))

from utils import summarize_period_variants, get_period_exclusion_reason  # type: ignore # noqa: E402

INITIALS = 'TK'


def _period(date, start, end, su=None, te=None, ro=None, kl=None, code='', **extra):
    return {
        'date': date,
        'startTime': start,
        'endTime': end,
        'code': code,
        'su': su if su is not None else [{'id': 1, 'name': 'MATH', 'longname': 'Mathematics'}],
        'te': te or [{'name': INITIALS}],
        'ro': ro or [],
        'kl': kl or [],
        **extra,
    }


def test_relevant_period_is_always_included_regardless_of_frequency():
    # Occurs on only 1 of 4 slot dates - still relevant, so still included.
    periods = [_period(20260907, 800, 845)]
    relevant, excluded = summarize_period_variants(periods, INITIALS, total_dates=4)

    assert len(relevant) == 1
    assert relevant[0]['occurrences'] == 1
    assert relevant[0]['frequency'] == 0.25
    assert excluded == []


def test_excluded_variant_below_one_third_is_dropped():
    # Irregular period occurring on 1 of 4 dates -> frequency 0.25 < 1/3.
    periods = [_period(20260907, 1400, 1445, code='irregular')]
    relevant, excluded = summarize_period_variants(periods, INITIALS, total_dates=4)

    assert relevant == []
    assert excluded == []


def test_excluded_variant_at_or_above_one_third_is_kept():
    # Same irregular period occurring on 2 of 6 dates -> frequency 1/3, kept.
    periods = [
        _period(20260907, 1400, 1445, code='irregular'),
        _period(20260921, 1400, 1445, code='irregular'),
    ]
    relevant, excluded = summarize_period_variants(periods, INITIALS, total_dates=6)

    assert relevant == []
    assert len(excluded) == 1
    variant = excluded[0]
    assert variant['occurrences'] == 2
    assert variant['frequency'] == 2 / 6
    assert variant['reason'] == 'irregular period'


def test_identical_relevant_periods_collapse_into_one_variant():
    periods = [
        _period(20260907, 800, 845),
        _period(20260921, 800, 845),
        _period(20261005, 800, 845),
    ]
    relevant, excluded = summarize_period_variants(periods, INITIALS, total_dates=3)

    assert len(relevant) == 1
    assert relevant[0]['occurrences'] == 3
    assert relevant[0]['frequency'] == 1.0
    assert excluded == []


def test_different_time_or_subject_variants_stay_distinct():
    periods = [
        _period(20260907, 800, 845),
        _period(20260921, 900, 945, su=[{'id': 2, 'name': 'GER', 'longname': 'German'}]),
    ]
    relevant, excluded = summarize_period_variants(periods, INITIALS, total_dates=2)

    assert len(relevant) == 2
    subjects = {v['subject'] for v in relevant}
    assert subjects == {'Mathematics', 'German'}


def test_on_call_substitution_excluded_with_reason():
    periods = [_period(20260907, 1000, 1045, su=[{'id': 255, 'name': 'VTR'}])] * 2
    relevant, excluded = summarize_period_variants(periods, INITIALS, total_dates=3)

    assert relevant == []
    assert len(excluded) == 1
    assert excluded[0]['reason'] == 'on-call substitution'


def test_cancelled_code_is_not_excluded():
    # 'cancelled' is deliberately not filtered - a single cancelled
    # occurrence shouldn't remove the slot from the regular schedule.
    assert get_period_exclusion_reason(_period(20260907, 800, 845, code='cancelled'), INITIALS) is None


def test_same_lesson_in_multiple_rooms_merges_into_one_variant():
    # WebUntis returns one period row per room for a lesson split across
    # rooms - same date/time/subject, different room. That's still just
    # one occurrence of one lesson, not two.
    periods = [
        _period(20260907, 800, 845, ro=[{'id': 1, 'name': 'GYM', 'longname': 'Gym A'}]),
        _period(20260907, 800, 845, ro=[{'id': 2, 'name': 'POOL', 'longname': 'Pool'}]),
    ]
    relevant, excluded = summarize_period_variants(periods, INITIALS, total_dates=1)

    assert len(relevant) == 1
    assert relevant[0]['occurrences'] == 1
    assert relevant[0]['frequency'] == 1.0
    assert relevant[0]['room'] == 'Gym A, Pool'
    assert excluded == []


def test_multi_room_lesson_occurring_on_several_dates_counts_dates_not_rows():
    periods = [
        _period(20260907, 800, 845, ro=[{'id': 1, 'name': 'GYM', 'longname': 'Gym A'}]),
        _period(20260907, 800, 845, ro=[{'id': 2, 'name': 'POOL', 'longname': 'Pool'}]),
        _period(20260914, 800, 845, ro=[{'id': 1, 'name': 'GYM', 'longname': 'Gym A'}]),
        _period(20260914, 800, 845, ro=[{'id': 2, 'name': 'POOL', 'longname': 'Pool'}]),
    ]
    relevant, _ = summarize_period_variants(periods, INITIALS, total_dates=2)

    assert len(relevant) == 1
    assert relevant[0]['occurrences'] == 2
    assert relevant[0]['frequency'] == 1.0


def test_subjectless_period_surfaces_name_candidates():
    # e.g. a break supervision slot (lstype 'bs') has no subject at all -
    # surface every plausible raw text field instead of guessing which one
    # is meaningful for this school.
    periods = [_period(
        20260907, 1000, 1015, su=[],
        lstype='bs', lstext='', info='Pausenaufsicht EG', activityType='', sg='',
    )]
    relevant, _ = summarize_period_variants(periods, INITIALS, total_dates=1)

    assert len(relevant) == 1
    variant = relevant[0]
    assert variant['subject'] is None
    assert variant['nameCandidates'] == {
        'activityType': None,
        'lstext': None,
        'info': 'Pausenaufsicht EG',
        'substText': None,
        'lstype': 'bs',
        'sg': None,
    }


def test_period_with_subject_has_no_name_candidates():
    periods = [_period(20260907, 800, 845)]
    relevant, _ = summarize_period_variants(periods, INITIALS, total_dates=1)

    assert relevant[0]['nameCandidates'] is None
