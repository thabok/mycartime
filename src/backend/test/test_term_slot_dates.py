"""
Unit tests for utils.get_term_slot_dates: fortnightly slots with alternating
A/B weeks, weekly slots without.
"""
import sys
from datetime import datetime
from pathlib import Path

backend_src = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(backend_src))

from utils import get_term_slot_dates  # type: ignore # noqa: E402

# Wednesday - the containing week (starting Monday 2026-09-07) is week A.
START = datetime(2026, 9, 9)
TERM_END = datetime(2026, 10, 9)


def test_alternating_weeks_step_fortnightly_and_offset_week_b():
    week_a_monday = get_term_slot_dates(START, TERM_END, 0)
    week_b_monday = get_term_slot_dates(START, TERM_END, 5)

    # Monday of week A (Sep 7) is before START, so the first match is two weeks on.
    assert week_a_monday == [datetime(2026, 9, 21), datetime(2026, 10, 5)]
    assert week_b_monday == [datetime(2026, 9, 14), datetime(2026, 9, 28)]


def test_non_alternating_weeks_step_weekly():
    fridays = get_term_slot_dates(START, TERM_END, 4, alternating_weeks=False)

    assert fridays == [
        datetime(2026, 9, 11), datetime(2026, 9, 18), datetime(2026, 9, 25),
        datetime(2026, 10, 2), datetime(2026, 10, 9),
    ]
