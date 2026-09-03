"""
Timetable service for querying schedules from WebUntis.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List

import config
import diskcache
import webuntis
from models import Member, Timetable
from utils import get_term_slot_dates, is_week_a_by_schoolyear, parse_time_to_hhmm, is_period_relevant

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
    
    def _get_schoolyear(self, for_date: datetime):
        """
        Get the WebUntis schoolyear that contains the given date.

        Args:
            for_date: Date to find the containing schoolyear for

        Returns:
            SchoolyearObject containing for_date. If for_date falls in a gap
            between schoolyears (e.g. the summer holidays), the next
            upcoming schoolyear is used; if for_date is after every known
            schoolyear, the last one is used. Either fallback is logged.
        """
        if not self.session:
            raise RuntimeError("Not connected to WebUntis. Call connect() first.")

        schoolyears = sorted(self.session.schoolyears(), key=lambda sy: sy.start)
        for schoolyear in schoolyears:
            if schoolyear.start <= for_date <= schoolyear.end:
                return schoolyear

        upcoming = next((sy for sy in schoolyears if sy.start > for_date), None)
        if upcoming:
            logger.warning(f"{for_date.date()} falls between schoolyears, using the upcoming one ({upcoming.name})")
            return upcoming

        logger.warning(f"No schoolyear found containing or after {for_date.date()}, falling back to the last known one")
        return schoolyears[-1]

    def get_suggested_reference_date(self, from_date: datetime = None) -> datetime:
        """
        Suggest a default reference date for the UI: the next date (today
        included) that falls in an A week, based on the school's own week
        numbering (first ISO week of the schoolyear is an A week).

        Args:
            from_date: Date to search forward from (defaults to now)

        Returns:
            The suggested date
        """
        from_date = from_date or datetime.now()
        schoolyear = self._get_schoolyear(from_date)

        candidate = from_date
        for _ in range(14):
            if is_week_a_by_schoolyear(candidate, schoolyear.start):
                return candidate
            candidate += timedelta(days=1)
        return candidate

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
        Get timetables for all members by scanning the whole current term.

        Instead of reading two concrete weeks (which requires the user to find
        a week with no irregularities), this queries from start_date to the end
        of the containing schoolyear, then for each of the 10 (weekday, A/B)
        slots merges every matching date's periods across the whole range to
        find the regular schedule. Makes ONE API call per member.

        Args:
            members: List of carpool members
            start_date: Date marking the start of the current schedule; the
                week containing this date is treated as week A

        Returns:
            Dictionary mapping member initials to their daily timetables
            Format: {initials: {day_num: Timetable}}
        """
        if not self.session:
            raise RuntimeError("Not connected to WebUntis. Call connect() first.")

        schoolyear = self._get_schoolyear(start_date)
        term_end = schoolyear.end
        # WebUntis rejects ranges that start before the containing schoolyear
        # (e.g. start_date falling in the summer holidays before term start).
        query_start = max(start_date, schoolyear.start)
        timetables = {}

        # Query once per member for the entire term (reduces API calls)
        for member in members:
            # Single API call for the whole term
            all_periods = self._query_timetable(member, query_start, term_end)

            # Extract member's ID from the data (needed for UI: web-link to schedule)
            member.id = next(
                (teacher.get('id') for period in all_periods
                 for teacher in period.get('te', [])
                 if teacher.get('name') == member.initials),
                None
            )

            # Filter relevant periods
            relevant_periods = [p for p in all_periods if is_period_relevant(p, member.initials)]
            logger.debug(f"Found {len(relevant_periods)} relevant periods (of {len(all_periods)} total) for {member.initials}")

            # Process each of the 10 (weekday, A/B) slots
            member_timetables = {}
            for day_num in range(10):
                slot_dates = {int(d.strftime('%Y%m%d')) for d in get_term_slot_dates(start_date, term_end, day_num)}
                slot_periods = [p for p in relevant_periods if p.get('date') in slot_dates]
                timetable = self._extract_timetable_for_day(member, day_num, slot_periods)

                # Apply custom day settings
                custom_day = member.get_custom_day(day_num)
                if custom_day:
                    if custom_day.ignore_completely:
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
                        # Set "is_present" flag if custom day prefs indicate presence
                        # This is important is members participate despite their webuntis
                        # schedule indicating absence
                        if timetable.start_time and timetable.end_time:
                            timetable.is_present = True
                        
                member_timetables[day_num] = timetable
            
            timetables[member.initials] = member_timetables
            
            # Store timetable in the member object
            member.timetable = member_timetables
        
        return timetables
    
    def _extract_timetable_for_day(
        self,
        member: Member,
        day_num: int,
        day_periods: List[dict]
    ) -> Timetable:
        """
        Build a Timetable for a (weekday, A/B) slot from its pre-filtered,
        possibly multi-week periods (already filtered by date and relevance
        by the caller).

        Args:
            member: Member object
            day_num: Day number (0-9)
            day_periods: Periods belonging to this slot, merged across every
                matching date in the scanned term

        Returns:
            Timetable object
        """
        try:
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
            logger.error(f"Error extracting timetable for {member.initials} (day {day_num}): {str(e)}")
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
