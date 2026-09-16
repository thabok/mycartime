"""
Isolated investigation/verification script (not part of the automated suite).

Verifies the full-term scan + auto-detected A/B weeks:
- get_timetables_for_members no longer requires a Monday start_date and
  aggregates the regular schedule across the whole term instead of reading
  two concrete weeks.
- get_suggested_reference_date returns a sensible default.
- The full calculate_driving_plan_logic pipeline still works end-to-end after
  removing start_date from calculate_driving_plan.

Usage:
    keyring.set_password("webuntis", "Kc", "<password>")   # once
    python backend/test/test_full_term_scan.py
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import keyring

backend_src = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(backend_src))

from timetable_service import TimetableService  # noqa: E402
from models import Member  # noqa: E402
from app import calculate_driving_plan_logic  # noqa: E402

USERNAME = "Kc"


def main():
    password = keyring.get_password("webuntis", USERNAME)
    if not password:
        print(f'No password found in keyring for service="webuntis" username="{USERNAME}".')
        sys.exit(1)

    # Deliberately NOT a Monday, to prove the Monday requirement is gone.
    # Also deliberately mid-term (not in the summer gap between schoolyears).
    start_date = datetime.now() - timedelta(days=7)
    while start_date.weekday() == 0:
        start_date += timedelta(days=1)
    print(f"Using start_date={start_date.date()} ({start_date.strftime('%A')}) -- intentionally not a Monday\n")

    with TimetableService() as ts:
        connected = ts.connect(USERNAME, password)
        print(f"Connected: {connected}\n")

        suggested = ts.get_suggested_reference_date()
        print(f"Suggested reference date (from today): {suggested.date()} ({suggested.strftime('%A')})")
        suggested_from_start = ts.get_suggested_reference_date(start_date)
        print(f"Suggested reference date (from start_date): {suggested_from_start.date()} "
              f"({suggested_from_start.strftime('%A')})\n")

        member = Member.from_dict({
            "firstName": "Test",
            "lastName": "Person",
            "initials": USERNAME,
            "numberOfSeats": 3,
        })

        timetables = ts.get_timetables_for_members([member], start_date)

        print(f"Member id resolved: {member.id}\n")
        print("10 (weekday, A/B) buckets:")
        for day_num in range(10):
            week = "A" if day_num < 5 else "B"
            weekday_idx = day_num % 5
            tt = timetables[USERNAME][day_num]
            print(f"  day_num={day_num} (weekday_idx={weekday_idx}, week {week}): "
                  f"present={tt.is_present} start={tt.start_time} end={tt.end_time}")

    print("\n--- Full pipeline sanity run (calculate_driving_plan_logic) ---")
    persons_data = [{
        "firstName": "Test",
        "lastName": "Person",
        "initials": USERNAME,
        "numberOfSeats": 3,
    }]
    try:
        plan = calculate_driving_plan_logic(
            persons_data=persons_data,
            start_date_str=start_date.strftime('%Y%m%d'),
            username=USERNAME,
            password=password,
        )
        print("Pipeline succeeded.")
        print(f"Summary: {plan.summary}")
        print(f"Day plans: {len(plan.day_plans)}")
    except Exception as e:
        print(f"Pipeline FAILED: {e}")
        raise


if __name__ == '__main__':
    main()
