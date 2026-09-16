"""
Utility functions for the Carpool Time backend service.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional

WEEKDAY_NAMES = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY']


def parse_time_to_hhmm(time_str: str) -> Optional[int]:
    """
    Parse time string (HH:MM) to HHMM integer format.
    
    Args:
        time_str: Time string in HH:MM format
        
    Returns:
        Integer in HHMM format or None if invalid
    """
    if not time_str or time_str == "":
        return None
    
    try:
        parts = time_str.split(':')
        if len(parts) != 2:
            return None
        
        hours = int(parts[0])
        minutes = int(parts[1])
        
        if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
            return None
        
        return hours * 100 + minutes
    except (ValueError, AttributeError):
        return None


def hhmm_to_minutes(hhmm: int) -> int:
    """
    Convert HHMM format to minutes since midnight.
    
    Args:
        hhmm: Time in HHMM format (e.g., 755 for 7:55)
        
    Returns:
        Minutes since midnight
    """
    hours = hhmm // 100
    minutes = hhmm % 100
    return hours * 60 + minutes


def minutes_to_hhmm(minutes: int) -> int:
    """
    Convert minutes since midnight to HHMM format.
    
    Args:
        minutes: Minutes since midnight
        
    Returns:
        Time in HHMM format
    """
    hours = minutes // 60
    mins = minutes % 60
    return hours * 100 + mins


def time_difference_minutes(time1: int, time2: int) -> int:
    """
    Calculate absolute difference between two times in minutes.
    
    Args:
        time1: First time in HHMM format
        time2: Second time in HHMM format
        
    Returns:
        Absolute difference in minutes
    """
    return abs(hhmm_to_minutes(time1) - hhmm_to_minutes(time2))


def times_within_tolerance(time1: int, time2: int, tolerance_minutes: int) -> bool:
    """
    Check if two times are within tolerance.
    
    Args:
        time1: First time in HHMM format
        time2: Second time in HHMM format
        tolerance_minutes: Maximum allowed difference in minutes
        
    Returns:
        True if times are within tolerance
    """
    return time_difference_minutes(time1, time2) <= tolerance_minutes


def get_period_exclusion_reason(period: dict, initials: str) -> Optional[str]:
    """
    Check whether a period should be excluded for the given teacher, and why.

    Note: WebUntis code=='cancelled' periods are deliberately NOT excluded
    here. A single cancelled occurrence doesn't mean the recurring slot isn't
    part of the regular schedule - we care about the series/general
    timetable (built from a whole term of occurrences), not what happened on
    one individual date.

    Args:
        period: Period data from WebUntis
        initials: Teacher initials

    Returns:
        None if the period is relevant, otherwise a short reason string
    """
    # Filter out irregular periods
    if period.get('code', '') == 'irregular':
        return 'irregular period'

    # Check if this is an on-call substitution (subject ID 255)
    ON_CALL_SUBSTITUTION_ID = 255
    # Check if this is a secondment period, i.e. "Abordnung" (subject ID 245) -
    # the teacher is at another school, so this period is not relevant here
    SECONDMENT_SUBJECT_ID = 245
    for subject in period.get('su', []):
        if subject.get('id') == ON_CALL_SUBSTITUTION_ID:
            return 'on-call substitution'
        if subject.get('id') == SECONDMENT_SUBJECT_ID:
            return 'secondment (teacher at another school)'

    # Check teachers
    different_orgid = False
    matching_name = False

    for teacher in period.get('te', []):
        if 'orgname' in teacher:
            if teacher['orgname'] == initials:
                # The period is handled by the specified teacher
                matching_name = True
            else:
                # The period is only handled temporarily by the specified teacher
                different_orgid = True
        elif 'name' in teacher and teacher['name'] == initials:
            matching_name = True

    # Period is irrelevant if there's a different org ID without a matching name
    if different_orgid and not matching_name:
        return 'handled by a different teacher'
    return None


def is_period_relevant(period: dict, initials: str) -> bool:
    """
    Check if a period is relevant for the given teacher.
    Filters out irregular periods and on-call substitutions.

    Args:
        period: Period data from WebUntis
        initials: Teacher initials

    Returns:
        True if the period is relevant for this teacher
    """
    return get_period_exclusion_reason(period, initials) is None


# A variant that was excluded on fewer than this fraction of the slot's real
# occurrences is treated as noise (e.g. a one-off substitution) rather than
# part of the regular schedule's story, and is dropped from the "excluded"
# breakdown.
EXCLUDED_VARIANT_FREQUENCY_THRESHOLD = 1 / 3


def _resolve_element_name(elements: list, names_by_id: Optional[Dict[int, str]]) -> Optional[str]:
    """
    Get the display name of the first element in a WebUntis period's element
    list (e.g. 'su', 'ro', 'kl'), preferring a name/longname already embedded
    on the element, falling back to an id lookup in a batch-fetched map.
    """
    if not elements:
        return None
    name = elements[0].get('longname') or elements[0].get('name')
    if not name and names_by_id:
        name = names_by_id.get(elements[0].get('id'))
    return name


# Raw WebUntis fields that might carry a human-readable name for a period
# that has no subject (e.g. break supervision, office hours - see 'lstype').
# All of them are surfaced whenever a period has no subject so a caller can
# see which one actually holds the useful text for a given school; none of
# these need id lookups, they're plain text already on the raw period.
_NAME_CANDIDATE_FIELDS = ['activityType', 'lstext', 'info', 'substText', 'lstype', 'sg']


def summarize_period_variants(
    periods: List[dict],
    initials: str,
    total_dates: int,
    subject_names: Optional[Dict[int, str]] = None,
    room_names: Optional[Dict[int, str]] = None,
    klasse_names: Optional[Dict[int, str]] = None,
) -> tuple:
    """
    Group a (weekday, A/B) slot's periods into distinct variants - by start
    time, end time, subject, class and exclusion reason - each annotated
    with how many of the slot's real calendar dates it appeared on.

    A single lesson taught across multiple rooms (e.g. a combined group
    split between two labs) shows up as one WebUntis period row per room,
    all sharing the same date/time/subject/class - room is therefore not
    part of the grouping key, just collected (comma-joined) per variant, so
    that case renders as one merged item instead of one per room.

    Args:
        periods: Periods belonging to a single slot (already date-filtered)
        initials: Teacher initials, used to determine relevance/reason
        total_dates: Total number of real calendar dates in this slot across
            the queried range (the frequency denominator)
        subject_names, room_names, klasse_names: Optional id -> display name
            maps, used as a fallback when a period's 'su'/'ro'/'kl' entry
            doesn't already carry a name/longname (WebUntis's raw timetable
            response only includes element IDs, so these are normally
            required to show the actual item/room/class names)

    Returns:
        (relevant_variants, excluded_variants) - relevant variants are
        always included (they directly explain the computed start/end
        time); excluded variants are only included if they occurred on at
        least EXCLUDED_VARIANT_FREQUENCY_THRESHOLD of the slot's dates,
        otherwise they're occasional noise, not part of the regular story.
    """
    groups = {}
    for period in periods:
        reason = get_period_exclusion_reason(period, initials)
        subject = _resolve_element_name(period.get('su', []), subject_names)
        room = _resolve_element_name(period.get('ro', []), room_names)
        klasse = _resolve_element_name(period.get('kl', []), klasse_names)
        teachers = period.get('te', [])
        teacher = (teachers[0].get('name') or teachers[0].get('orgname')) if teachers else None

        key = (period.get('startTime'), period.get('endTime'), subject, klasse, reason)
        if key not in groups:
            groups[key] = {
                'startTime': period.get('startTime'),
                'endTime': period.get('endTime'),
                'subject': subject,
                'klasse': klasse,
                'teacher': teacher,
                'rooms': set(),
                'dates': set(),
                'reason': reason,
                # Not every school/period type populates these the same way,
                # so grab them once per variant rather than guessing which
                # one is "the" name - see _NAME_CANDIDATE_FIELDS.
                'nameCandidates': (
                    {field: period.get(field) or None for field in _NAME_CANDIDATE_FIELDS}
                    if not subject else None
                ),
            }
        if room:
            groups[key]['rooms'].add(room)
        groups[key]['dates'].add(period.get('date'))

    relevant_variants = []
    excluded_variants = []
    for variant in groups.values():
        reason = variant.pop('reason')
        dates = variant.pop('dates')
        rooms = variant.pop('rooms')
        variant['room'] = ', '.join(sorted(rooms)) if rooms else None
        variant['occurrences'] = len(dates)
        variant['frequency'] = (variant['occurrences'] / total_dates) if total_dates else 0.0
        if reason is None:
            relevant_variants.append(variant)
        elif variant['frequency'] >= EXCLUDED_VARIANT_FREQUENCY_THRESHOLD:
            variant['reason'] = reason
            excluded_variants.append(variant)

    return relevant_variants, excluded_variants


def get_earliest_time(times: list) -> Optional[int]:
    """
    Get the earliest time from a list of times.
    
    Args:
        times: List of times in HHMM format
        
    Returns:
        Earliest time or None if list is empty
    """
    if not times:
        return None
    return min(times)


def get_latest_time(times: list) -> Optional[int]:
    """
    Get the latest time from a list of times.
    
    Args:
        times: List of times in HHMM format
        
    Returns:
        Latest time or None if list is empty
    """
    if not times:
        return None
    return max(times)


def format_hhmm(hhmm: int) -> str:
    """
    Format HHMM integer to HH:MM string.
    
    Args:
        hhmm: Time in HHMM format
        
    Returns:
        Time string in HH:MM format
    """
    hours = hhmm // 100
    minutes = hhmm % 100
    return f"{hours:02d}:{minutes:02d}"


def parse_date_yymmdd(date_str: str) -> datetime:
    """
    Parse date string in YYYYMMDD format.
    
    Args:
        date_str: Date string in YYYYMMDD format (e.g., "20251223")
        
    Returns:
        datetime object
    """
    return datetime.strptime(date_str, "%Y%m%d")


def get_term_slot_dates(start_date: datetime, term_end: datetime, day_number: int) -> List[datetime]:
    """
    Get every real calendar date between start_date and term_end that belongs to a
    given (weekday, A/B-week) slot of the 10-slot cycle. The week containing
    start_date is always treated as week A, regardless of which weekday start_date
    itself falls on; dates before start_date are excluded (they belong to a
    schedule that's no longer current).

    Args:
        start_date: Date marking the start of the current schedule (any weekday)
        term_end: Last date to consider (e.g. end of the containing schoolyear)
        day_number: 0-9, where day_number % 5 is the weekday (0=Monday) and
            day_number < 5 means week A, day_number >= 5 means week B

    Returns:
        List of matching dates, in chronological order
    """
    weekday_index = day_number % 5
    target_is_week_a = day_number < 5

    start_monday = start_date - timedelta(days=start_date.weekday())
    anchor = start_monday + timedelta(days=weekday_index)
    if not target_is_week_a:
        anchor += timedelta(days=7)
    while anchor < start_date:
        anchor += timedelta(days=14)

    dates = []
    d = anchor
    while d <= term_end:
        dates.append(d)
        d += timedelta(days=14)
    return dates


def is_week_a_by_schoolyear(date: datetime, schoolyear_start: datetime) -> bool:
    """
    Determine whether a date falls in an "A week" purely from the school's own
    week numbering: the first ISO calendar week of the schoolyear is always an
    A week, and A/B alternates with ISO week-number parity from there.

    This is only meant for suggesting a sensible default reference date in the
    UI -- actual timetable aggregation anchors A/B to whatever date the user
    ends up selecting (see get_term_slot_dates), not to this schoolyear-based
    numbering.

    Args:
        date: Date to classify
        schoolyear_start: Start date of the schoolyear (from WebUntis)

    Returns:
        True if the date's ISO week has the same parity as the schoolyear's
        first ISO week
    """
    return date.isocalendar()[1] % 2 == schoolyear_start.isocalendar()[1] % 2
