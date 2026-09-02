"""
Utility functions for the Carpool Time backend service.
"""
from datetime import datetime, timedelta
from typing import List, Optional

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
    # Filter out irregular periods
    if period.get('code', '') == 'irregular':
        return False
    
    # Check if this is an on-call substitution (subject ID 255)
    ON_CALL_SUBSTITUTION_ID = 255
    # Check if this is a secondment period, i.e. "Abordnung" (subject ID 245) -
    # the teacher is at another school, so this period is not relevant here
    SECONDMENT_SUBJECT_ID = 245
    for subject in period.get('su', []):
        if subject.get('id') in [ON_CALL_SUBSTITUTION_ID, SECONDMENT_SUBJECT_ID]:
            return False

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
    is_irrelevant = different_orgid and not matching_name
    return not is_irrelevant


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
