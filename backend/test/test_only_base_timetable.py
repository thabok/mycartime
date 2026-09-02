"""
Isolated investigation script (not part of the automated suite).

Compares onlyBaseTimetable=True vs onlyBaseTimetable=False for the same date
range against a live WebUntis account, to determine whether that flag returns
the regular/master schedule (ignoring substitutions, cancellations, class
trips, etc.) instead of what actually happened on those dates.

python-webuntis's session.py hardcodes onlyBaseTimetable=False in
_timetable_extended_raw, so we bypass that by calling session._request(...)
directly with our own options dict.

Usage:
    keyring.set_password("webuntis", "Kc", "<password>")   # once
    python backend/test/test_only_base_timetable.py
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import keyring

backend_src = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(backend_src))

import config  # noqa: E402
import webuntis  # noqa: E402

USERNAME = "Kc"
TEACHER_ELEMENT_TYPE = 2


def query_timetable(session, start, end, only_base):
    element = {"id": USERNAME, "type": TEACHER_ELEMENT_TYPE, "keyType": "name"}
    options = {
        "element": element,
        "startDate": int(start.strftime('%Y%m%d')),
        "endDate": int(end.strftime('%Y%m%d')),
        "teacherFields": ["id", "name", "externalkey"],
        "onlyBaseTimetable": only_base,
        "showBooking": True,
        "showInfo": True,
        "showSubstText": True,
        "showLsText": True,
        "showLsNumber": True,
        "showStudentgroup": True,
    }
    return session._request('getTimetable', {"options": options})


def period_key(p):
    teachers = tuple(sorted(t.get('name', t.get('orgname', '?')) for t in p.get('te', [])))
    return (p.get('date'), p.get('startTime'), p.get('endTime'), teachers)


def summarize(p):
    return {
        'date': p.get('date'),
        'start': p.get('startTime'),
        'end': p.get('endTime'),
        'code': p.get('code', ''),
        'info': p.get('info', ''),
        'substText': p.get('substText', ''),
        'subjects': [s.get('id') for s in p.get('su', [])],
    }


def main():
    password = keyring.get_password("webuntis", USERNAME)
    if not password:
        print(f'No password found in keyring for service="webuntis" username="{USERNAME}".')
        print(f'Set it first: keyring.set_password("webuntis", "{USERNAME}", "<password>")')
        sys.exit(1)

    session = webuntis.Session(
        server=config.WEBUNTIS_SERVER,
        school=config.WEBUNTIS_SCHOOL,
        username=USERNAME,
        password=password,
        useragent=config.WEBUNTIS_USERAGENT,
    )
    session.login()
    print(f"Logged in as {USERNAME}\n")

    try:
        today = datetime.now()
        schoolyears = session.schoolyears()
        current_sy = next((sy for sy in schoolyears if sy.start <= today <= sy.end), schoolyears[-1])
        print(f"Current schoolyear: {current_sy.name} ({current_sy.start.date()} .. {current_sy.end.date()})")

        start = max(today - timedelta(weeks=8), current_sy.start)
        end = min(today + timedelta(weeks=4), current_sy.end)

        print(f"Querying {start.date()} .. {end.date()} with onlyBaseTimetable=False (actual) ...")
        actual = query_timetable(session, start, end, False)
        print(f"  -> {len(actual)} periods")

        print(f"Querying {start.date()} .. {end.date()} with onlyBaseTimetable=True (base) ...")
        base = query_timetable(session, start, end, True)
        print(f"  -> {len(base)} periods")

        actual_by_key = {period_key(p): p for p in actual}
        base_by_key = {period_key(p): p for p in base}

        only_in_actual = set(actual_by_key) - set(base_by_key)
        only_in_base = set(base_by_key) - set(actual_by_key)
        common = set(actual_by_key) & set(base_by_key)

        print(f"\nCommon periods (same date/time/teacher): {len(common)}")
        print(f"Only in ACTUAL (onlyBaseTimetable=False): {len(only_in_actual)}")
        print(f"Only in BASE   (onlyBaseTimetable=True):  {len(only_in_base)}")

        if only_in_actual:
            print("\n--- Periods only in ACTUAL (one-off events/substitutions not in the base plan) ---")
            for k in sorted(only_in_actual)[:20]:
                print(" ", summarize(actual_by_key[k]))
                print("    RAW:", actual_by_key[k])

        if only_in_base:
            print("\n--- Periods only in BASE (regular periods suppressed/moved in actual, e.g. cancelled) ---")
            for k in sorted(only_in_base)[:20]:
                print(" ", summarize(base_by_key[k]))

        differing = []
        for k in common:
            a_sum, b_sum = summarize(actual_by_key[k]), summarize(base_by_key[k])
            if a_sum != b_sum:
                differing.append((k, a_sum, b_sum))

        print(f"\nPeriods present in both but with differing fields: {len(differing)}")
        for k, a_sum, b_sum in differing[:20]:
            print(f"  {k}")
            print(f"    actual: {a_sum}")
            print(f"    base:   {b_sum}")

        irregular_actual = [p for p in actual if p.get('code') == 'irregular']
        print(f"\nPeriods coded 'irregular' in ACTUAL: {len(irregular_actual)}")
        for p in irregular_actual[:10]:
            in_base = period_key(p) in base_by_key
            print(f"  {summarize(p)}  -- present in BASE too: {in_base}")

        cancelled_actual = [p for p in actual if p.get('code') == 'cancelled']
        print(f"\nPeriods coded 'cancelled' in ACTUAL: {len(cancelled_actual)}")
        for p in cancelled_actual[:10]:
            in_base = period_key(p) in base_by_key
            print(f"  {summarize(p)}  -- present in BASE too: {in_base}")

    finally:
        session.logout()
        print("\nLogged out.")


if __name__ == '__main__':
    main()
