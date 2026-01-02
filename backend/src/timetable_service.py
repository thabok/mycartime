"""
Timetable service for querying schedules from WebUntis.
"""
import logging
from datetime import datetime
from typing import Dict, List

import config
import diskcache
import webuntis
from models import Member, Timetable
from utils import get_week_dates, parse_time_to_hhmm, is_period_relevant

logger = logging.getLogger(__name__)


class TimetableService:
    """Service for connecting to WebUntis and retrieving timetables."""
    
    def __init__(self, server: str = None, school: str = None, useragent: str = None, use_cache: bool = True):
        """
        Initialize the timetable service.
        
        Args:
            server: WebUntis server URL
            school: School name
            useragent: User agent string
            use_cache: Whether to use disk cache for timetable queries
        """
        self.server = server or config.WEBUNTIS_SERVER
        self.school = school or config.WEBUNTIS_SCHOOL
        self.useragent = useragent or config.WEBUNTIS_USERAGENT
        self.session = None
        self.use_cache = use_cache
        self.cache = diskcache.Cache(config.CACHE_DIR) if use_cache else None
    
    def connect(self, username: str, password: str) -> bool:
        """
        Connect to WebUntis using credentials.
        
        Args:
            username: WebUntis username
            password: WebUntis password (hashed)
            
        Returns:
            True if connection successful
        """
        try:
            self.session = webuntis.Session(
                server=self.server,
                school=self.school,
                username=username,
                password=password,
                useragent=self.useragent
            )
            self.session.login()
            logger.info(f"Successfully connected to WebUntis for user {username}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to WebUntis: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from WebUntis."""
        if self.session:
            try:
                self.session.logout()
                logger.info("Disconnected from WebUntis")
            except Exception as e:
                logger.warning(f"Error during disconnect: {str(e)}")
            finally:
                self.session = None
    
    def clear_cache(self):
        """Clear all cached timetable data."""
        if self.cache:
            self.cache.clear()
            logger.info("Timetable cache cleared")
    
    def _get_cache_key(self, member_initials: str, start_date: datetime, end_date: datetime) -> str:
        """Generate cache key for a timetable query."""
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')
        return f"timetable-{member_initials}-{start_str}-{end_str}"
    
    def _query_timetable_raw(self, member: Member, start_date: datetime, end_date: datetime) -> List[dict]:
        """Query timetable from WebUntis API (bypasses cache)."""
        if not self.session:
            raise RuntimeError("Not connected to WebUntis. Call connect() first.")
        
        try:
            # Convert dates to WebUntis format (YYYYMMDD as integer)
            start_int = int(start_date.strftime('%Y%m%d'))
            end_int = int(end_date.strftime('%Y%m%d'))
            
            logger.debug(f"Querying WebUntis API for {member.initials} from {start_int} to {end_int}")
            
            # Query timetable for the teacher
            tte = self.session.timetable_extended(
                start=start_int,
                end=end_int,
                key_type="name",
                teacher_fields=["id", "name", "externalkey"],
                teacher=member.initials
            )
            
            periods = tte._data
            logger.info(f"Retrieved {len(periods)} periods for {member.initials}")
            return periods
            
        except Exception as e:
            logger.error(f"Error querying timetable for {member.initials}: {str(e)}")
            return []
    
    def _query_timetable(self, member: Member, start_date: datetime, end_date: datetime) -> List[dict]:
        """Query timetable with caching support."""
        # Check cache first
        if self.cache is not None:
            cache_key = self._get_cache_key(member.initials, start_date, end_date)
            cached_data = self.cache.get(cache_key)
            
            if cached_data is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_data
            
            logger.debug(f"Cache miss for {cache_key}, fetching from API")
        
        # Fetch from API
        logger.info(f"Fetching timetable for {member.initials} from {start_date.date()} to {end_date.date()}")
        periods = self._query_timetable_raw(member, start_date, end_date)
        
        # Store in cache with TTL
        if self.cache is not None and periods:
            cache_key = self._get_cache_key(member.initials, start_date, end_date)
            self.cache.set(cache_key, periods, expire=config.CACHE_TTL_SECONDS)
            logger.debug(f"Cached {len(periods)} periods for {cache_key}")
        
        return periods
    
    def get_timetables_for_members(
        self, 
        members: List[Member], 
        start_date: datetime
    ) -> Dict[str, Dict[int, Timetable]]:
        """
        Get timetables for all members for the 2-week cycle.
        Makes ONE API call per member for entire date range.
        
        Args:
            members: List of carpool members
            start_date: Starting Monday of the cycle
            
        Returns:
            Dictionary mapping member initials to their daily timetables
            Format: {initials: {day_num: Timetable}}
        """
        if not self.session:
            raise RuntimeError("Not connected to WebUntis. Call connect() first.")
        
        dates = get_week_dates(start_date)
        end_date = dates[-1]  # Last date in the 2-week cycle
        timetables = {}
        
        # Query once per member for the entire date range (reduces API calls)
        for member in members:
            # Single API call for entire date range
            all_periods = self._query_timetable(member, start_date, end_date)
            
            # Filter relevant periods
            relevant_periods = [p for p in all_periods if is_period_relevant(p, member.initials)]
            logger.debug(f"Found {len(relevant_periods)} relevant periods (of {len(all_periods)} total) for {member.initials}")
            
            # Process each day
            member_timetables = {}
            for day_num, date in enumerate(dates):
                timetable = self._extract_timetable_for_day(member, date, day_num, relevant_periods)
                
                # Apply custom day settings
                custom_day = member.get_custom_day(day_num)
                if custom_day:
                    if custom_day.ignore_completely:
                        timetable.is_present = False
                    elif custom_day.skip_morning and custom_day.skip_afternoon:
                        timetable.is_present = False
                    else:
                        # Apply custom start/end times
                        if custom_day.custom_start:
                            custom_start = parse_time_to_hhmm(custom_day.custom_start)
                            if custom_start:
                                timetable.start_time = custom_start
                        
                        if custom_day.custom_end:
                            custom_end = parse_time_to_hhmm(custom_day.custom_end)
                            if custom_end:
                                timetable.end_time = custom_end
                        
                        # Handle skip morning/afternoon
                        if custom_day.skip_morning:
                            timetable.start_time = None
                        if custom_day.skip_afternoon:
                            timetable.end_time = None
                
                member_timetables[day_num] = timetable
            
            timetables[member.initials] = member_timetables
            
            # Store timetable in the member object
            member.timetable = member_timetables
        
        return timetables
    
    def _extract_timetable_for_day(
        self, 
        member: Member, 
        date: datetime, 
        day_num: int,
        relevant_periods: List[dict]
    ) -> Timetable:
        """
        Extract timetable for a specific day from pre-fetched periods.
        
        Args:
            member: Member object
            date: Date to query
            day_num: Day number (0-9)
            relevant_periods: Already filtered relevant periods for this member
            
        Returns:
            Timetable object
        """
        try:
            # Filter periods for this specific date
            date_int = int(date.strftime('%Y%m%d'))
            day_periods = [p for p in relevant_periods if p.get('date') == date_int]
            
            if not day_periods:
                # No lessons on this day
                return Timetable(
                    member_initials=member.initials,
                    day_number=day_num,
                    start_time=None,
                    end_time=None,
                    is_present=False
                )
            
            # Find earliest start and latest end time
            start_time = min(p.get('startTime', 9999) for p in day_periods)
            end_time = max(p.get('endTime', 0) for p in day_periods)
            
            return Timetable(
                member_initials=member.initials,
                day_number=day_num,
                start_time=start_time,
                end_time=end_time,
                is_present=True
            )
            
        except Exception as e:
            logger.error(f"Error extracting timetable for {member.initials} on {date}: {str(e)}")
            # Return an absent timetable
            return Timetable(
                member_initials=member.initials,
                day_number=day_num,
                start_time=None,
                end_time=None,
                is_present=False
            )
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
