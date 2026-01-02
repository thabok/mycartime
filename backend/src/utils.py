"""
Utility functions for the Carpool Time backend service.
"""
from datetime import datetime, timedelta
from typing import Optional


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
    for subject in period.get('su', []):
        if subject.get('id') == ON_CALL_SUBSTITUTION_ID:
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


def get_week_dates(start_date: datetime) -> list:
    """
    Get list of dates for 2-week cycle starting from Monday.
    
    Args:
        start_date: Starting Monday date
        
    Returns:
        List of 10 dates (5 days x 2 weeks)
    """
    dates = []
    # Week A: Monday to Friday
    for i in range(5):
        dates.append(start_date + timedelta(days=i))
    # Week B: Monday to Friday (next week)
    for i in range(7, 12):
        dates.append(start_date + timedelta(days=i))
    return dates


def get_day_of_week_name(date: datetime) -> str:
    """
    Get day of week name.
    
    Args:
        date: datetime object
        
    Returns:
        Day name (MONDAY, TUESDAY, etc.)
    """
    days = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']
    return days[date.weekday()]
