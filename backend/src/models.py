"""
Data models for the Carpool Time backend service.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, time


@dataclass
class TimeInfo:
    """Holds time information with sources for transparency."""
    timetable_time: Optional[int] = None  # Time from timetable (HHMM format)
    custom_pref_time: Optional[int] = None  # Time from custom preference (HHMM format)
    effective_time: int = None  # Time used for party assignment (HHMM format)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'timetableTime': self.timetable_time,
            'customPrefTime': self.custom_pref_time,
            'effectiveTime': self.effective_time
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TimeInfo':
        """Create TimeInfo from dictionary."""
        return cls(
            timetable_time=data.get('timetableTime'),
            custom_pref_time=data.get('customPrefTime'),
            effective_time=data.get('effectiveTime')
        )


@dataclass
class CustomDay:
    """Custom day configuration for a member."""
    ignore_completely: bool = False
    no_waiting_afternoon: bool = False
    needs_car: bool = False
    driving_skip: bool = False
    skip_morning: bool = False
    skip_afternoon: bool = False
    custom_start: Optional[str] = None  # HH:MM format
    custom_end: Optional[str] = None    # HH:MM format

    @classmethod
    def from_dict(cls, data: dict) -> 'CustomDay':
        """Create CustomDay from dictionary."""
        return cls(
            ignore_completely=data.get('ignoreCompletely', False),
            no_waiting_afternoon=data.get('noWaitingAfternoon', False),
            needs_car=data.get('needsCar', False),
            driving_skip=data.get('drivingSkip', False),
            skip_morning=data.get('skipMorning', False),
            skip_afternoon=data.get('skipAfternoon', False),
            custom_start=data.get('customStart') or None,
            custom_end=data.get('customEnd') or None
        )


@dataclass
class Member:
    """Represents a carpool party member."""
    first_name: str
    last_name: str
    initials: str
    number_of_seats: int
    is_part_time: bool = False
    custom_days: Dict[int, CustomDay] = field(default_factory=dict)
    
    # Runtime fields (populated during algorithm execution)
    drive_count: int = 0
    max_drives: int = 0
    timetable: Dict[int, 'Timetable'] = field(default_factory=dict)  # Populated by timetable_service
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Member':
        """Create Member from dictionary."""
        custom_days = {}
        if 'customDays' in data:
            for day_num, day_data in data['customDays'].items():
                custom_days[int(day_num)] = CustomDay.from_dict(day_data)
        
        return cls(
            first_name=data['firstName'],
            last_name=data['lastName'],
            initials=data['initials'],
            number_of_seats=data['numberOfSeats'],
            is_part_time=data.get('isPartTime', False),
            custom_days=custom_days
        )
    
    def get_custom_day(self, day_num: int) -> Optional[CustomDay]:
        """Get custom day configuration for a specific day."""
        return self.custom_days.get(day_num)
    
    def should_ignore_on_day(self, day_num: int) -> bool:
        """
        Check if member should be ignored on a specific day.
        
        Args:
            day_num: Day number (0-9)
            timetable: Optional timetable for this day
            
        Returns:
            True if member should be ignored (day off or custom ignore)
        """
        # Check custom day settings first
        custom = self.get_custom_day(day_num)
        if custom and custom.ignore_completely:
            return True
        
        # Check if member has a schedule for this day
        has_timetable = day_num in self.timetable and self.timetable[day_num].is_present
        
        # Check if member has custom times that override the schedule
        has_custom_times = custom and (custom.custom_start or custom.custom_end)
        
        # Member should be ignored if they have neither timetable nor custom times
        return not has_timetable and not has_custom_times
    
    def needs_car_on_day(self, day_num: int) -> bool:
        """Check if member needs a car on a specific day.
        This means that the person cannot be a passenger, they must be a driver!"""
        custom = self.get_custom_day(day_num)
        return custom.needs_car if custom else False
    
    def skip_morning_on_day(self, day_num: int) -> bool:
        """Check if member skips morning (schoolbound) on a specific day."""
        custom = self.get_custom_day(day_num)
        return custom.skip_morning if custom else False
    
    def skip_afternoon_on_day(self, day_num: int) -> bool:
        """Check if member skips afternoon (homebound) on a specific day."""
        custom = self.get_custom_day(day_num)
        return custom.skip_afternoon if custom else False
    
    def no_waiting_afternoon_on_day(self, day_num: int) -> bool:
        """Check if member has no waiting afternoon on a specific day."""
        custom = self.get_custom_day(day_num)
        return custom.no_waiting_afternoon if custom else False
    
    def get_tolerance_for_direction(self, day_num: int, schoolbound: bool, default_tolerance: int) -> int:
        """
        Get the time tolerance for a specific direction on a specific day.
        Returns 0 if noWaitingAfternoon is set and direction is homebound, otherwise default.
        """
        if not schoolbound and self.no_waiting_afternoon_on_day(day_num):
            return 0
        return default_tolerance
    
    def validate_custom_day(self, day_num: int) -> List[str]:
        """
        Validate custom day settings and return list of validation errors.
        
        Returns:
            List of error messages, empty if valid
        """
        custom = self.get_custom_day(day_num)
        if not custom:
            return []
        
        errors = []
        
        # needsCar is mutually exclusive with drivingSkip
        if custom.needs_car and custom.driving_skip:
            errors.append(f"Day {day_num}: needsCar and drivingSkip are mutually exclusive")
        
        # skipMorning requires needsCar
        if custom.skip_morning and not custom.needs_car:
            errors.append(f"Day {day_num}: skipMorning requires needsCar to be true")
        
        # skipAfternoon requires needsCar
        if custom.skip_afternoon and not custom.needs_car:
            errors.append(f"Day {day_num}: skipAfternoon requires needsCar to be true")
        
        # noWaitingAfternoon is mutually exclusive with skipAfternoon
        if custom.no_waiting_afternoon and custom.skip_afternoon:
            errors.append(f"Day {day_num}: noWaitingAfternoon and skipAfternoon are mutually exclusive")
        
        return errors
    
    def can_drive_on_day(self, day_num: int, desperate: bool = False) -> bool:
        """
        Check if member can drive on a specific day.
        
        Args:
            day_num: Day number (0-9)
            desperate: Optional flag if the plan desperately needs this member to drive
            
        Returns:
            True if member can drive (has schedule or custom times, not ignored, not needs_car, not driving_skip or desperate)
        """
        should_ignore = self.should_ignore_on_day(day_num)
        if should_ignore:
            return False
        # Check custom day settings first
        if not desperate:
            custom = self.get_custom_day(day_num)
            if custom and custom.driving_skip:
                return False
        # No reason why this member cannot drive
        return True


@dataclass
class DayOfWeekABCombo:
    """Represents a day in the 2-week cycle."""
    day_of_week: str  # MONDAY, TUESDAY, etc.
    is_week_a: bool
    unique_number: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'dayOfWeek': self.day_of_week,
            'isWeekA': self.is_week_a,
            'uniqueNumber': self.unique_number
        }


@dataclass
class Party:
    """Represents a carpool party (one direction, one time)."""
    day_of_week_ab_combo: DayOfWeekABCombo
    driver: str  # initials
    time: int  # HHMM format
    passengers: List[str]  # list of initials
    is_designated_driver: bool
    drives_despite_custom_prefs: bool
    schoolbound: bool
    is_lonely_driver: bool = False  # True if driver has skipMorning/skipAfternoon
    pool_name: Optional[str] = None  # Unique pool identifier (e.g. "pool-mon-a-schoolbound-755-tol30")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            'dayOfWeekABCombo': self.day_of_week_ab_combo.to_dict(),
            'driver': self.driver,
            'time': self.time,
            'passengers': self.passengers,
            'isDesignatedDriver': self.is_designated_driver,
            'drivesDespiteCustomPrefs': self.drives_despite_custom_prefs,
            'schoolbound': self.schoolbound,
            'isLonelyDriver': self.is_lonely_driver
        }
        if self.pool_name:
            result['poolName'] = self.pool_name
        return result


@dataclass
class DayPlan:
    """Represents the plan for a single day."""
    day_of_week_ab_combo: DayOfWeekABCombo
    parties: List[Party] = field(default_factory=list)
    schoolbound_times_by_initials: Dict[str, int] = field(default_factory=dict)  # DEPRECATED: use schoolbound_time_info_by_initials
    homebound_times_by_initials: Dict[str, int] = field(default_factory=dict)  # DEPRECATED: use homebound_time_info_by_initials
    schoolbound_time_info_by_initials: Dict[str, TimeInfo] = field(default_factory=dict)  # Time information with sources
    homebound_time_info_by_initials: Dict[str, TimeInfo] = field(default_factory=dict)  # Time information with sources
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'dayOfWeekABCombo': self.day_of_week_ab_combo.to_dict(),
            'parties': [p.to_dict() for p in self.parties],
            'schoolboundTimesByInitials': self.schoolbound_times_by_initials,  # Keep for backward compat
            'homeboundTimesByInitials': self.homebound_times_by_initials,  # Keep for backward compat
            'schoolboundTimeInfoByInitials': {k: v.to_dict() for k, v in self.schoolbound_time_info_by_initials.items()},
            'homeboundTimeInfoByInitials': {k: v.to_dict() for k, v in self.homebound_time_info_by_initials.items()}
        }


@dataclass
class DrivingPlan:
    """Represents the complete driving plan for 2 weeks."""
    summary: str
    day_plans: Dict[int, DayPlan] = field(default_factory=dict)
    member_id_map: Dict[str, Optional[int]] = field(default_factory=dict)
    schedule_url_template: str = 'https://ngw-wilhelmshaven.webuntis.com/timetable/teacher?date=DATE&entityId=TEACHER_ID'
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'summary': self.summary,
            'dayPlans': {str(k): v.to_dict() for k, v in self.day_plans.items()},
            'memberIdMap': self.member_id_map,
            'scheduleUrlTemplate': self.schedule_url_template
        }


@dataclass
class Timetable:
    """Represents a member's timetable for a day."""
    member_initials: str
    day_number: int  # 0-9 for the 10 days in the cycle
    start_time: Optional[int] = None  # HHMM format (may be overwritten by custom prefs)
    end_time: Optional[int] = None    # HHMM format (may be overwritten by custom prefs)
    scheduled_start_time: Optional[int] = None  # Original timetable start time (never overwritten)
    scheduled_end_time: Optional[int] = None    # Original timetable end time (never overwritten)
    is_present: bool = True
    
    def __post_init__(self):
        """Initialize scheduled times from start/end times after creation."""
        if self.scheduled_start_time is None:
            self.scheduled_start_time = self.start_time
        if self.scheduled_end_time is None:
            self.scheduled_end_time = self.end_time
    
    def get_start_time(self) -> Optional[int]:
        """Get the effective start time (may include custom preferences)."""
        return self.start_time if self.is_present else None
    
    def get_end_time(self) -> Optional[int]:
        """Get the effective end time (may include custom preferences)."""
        return self.end_time if self.is_present else None
    
    def get_scheduled_start_time(self) -> Optional[int]:
        """Get the original scheduled start time from timetable (never overwritten)."""
        return self.scheduled_start_time if self.is_present else None
    
    def get_scheduled_end_time(self) -> Optional[int]:
        """Get the original scheduled end time from timetable (never overwritten)."""
        return self.scheduled_end_time if self.is_present else None
