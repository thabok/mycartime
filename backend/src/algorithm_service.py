"""
Core algorithm service for calculating optimal driving plans.
"""
import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import config
from models import DayOfWeekABCombo, DayPlan, DrivingPlan, Member, Party
from utils import (get_day_of_week_name, get_earliest_time, get_latest_time,
                   get_week_dates, times_within_tolerance)

logger = logging.getLogger(__name__)


class TimeSlot:
    """Represents a time slot with members who need to travel."""
    def __init__(self, time: int, schoolbound: bool):
        self.time = time
        self.schoolbound = schoolbound
        self.members: Set[str] = set()  # member initials
    
    def add_member(self, initials: str):
        """Add a member to this time slot."""
        self.members.add(initials)
    
    def __repr__(self):
        direction = "to school" if self.schoolbound else "home"
        return f"TimeSlot({self.time}, {direction}, {len(self.members)} members)"


class DriverPool:
    """Represents a pool of potential drivers for a time slot."""
    def __init__(self, time_slot: TimeSlot, day_num: int, schoolbound: bool):
        self.time_slot = time_slot
        self.day_num = day_num
        self.schoolbound = schoolbound
        self.candidates: List[str] = []  # member initials who can drive
        self.passengers: List[str] = []  # member initials who need rides
        # Track all assignments: each is (driver, list of passengers for that driver)
        self.assignments: List[Tuple[str, List[str]]] = []
        self.covered_members: Set[str] = set()  # Members who have been assigned to a party
    
    @property
    def size(self) -> int:
        """Number of potential drivers (excluding those already assigned)."""
        return len([c for c in self.candidates if c not in self.covered_members])
    
    @property
    def is_mandatory(self) -> bool:
        """True if this is a mandatory driver (only 1 candidate available)."""
        return len(self.candidates) == 1
    
    @property
    def is_fully_assigned(self) -> bool:
        """True if all members in the pool have been assigned to parties."""
        all_members = self.time_slot.members
        return all(m in self.covered_members for m in all_members)
    
    @property
    def remaining_members(self) -> Set[str]:
        """Members who still need to be assigned."""
        return self.time_slot.members - self.covered_members
    
    def add_assignment(self, driver: str, passengers: List[str]) -> None:
        """Add a driver assignment and mark members as covered."""
        self.assignments.append((driver, passengers))
        self.covered_members.add(driver)
        self.covered_members.update(passengers)
    
    def __repr__(self):
        direction = "to school" if self.schoolbound else "home"
        total = len(self.time_slot.members)
        covered = len(self.covered_members)
        return f"DriverPool(day={self.day_num + 1}, {direction}, {covered}/{total} covered, {len(self.assignments)} parties)"


class AlgorithmService:
    """Service for calculating optimal driving plans."""
    
    def __init__(self, tolerance_minutes: int = None):
        """
        Initialize the algorithm service.
        
        Args:
            tolerance_minutes: Time tolerance for grouping members
        """
        self.tolerance = tolerance_minutes or config.TIME_TOLERANCE_MINUTES
        self.members: Dict[str, Member] = {}
    
    def calculate_driving_plan(
        self,
        members: List[Member],
        start_date: datetime
    ) -> DrivingPlan:
        """
        Calculate the optimal driving plan for all members.
        
        This algorithm works in three phases:
        1. Create pools (grouped by day, direction, time slot)
        2. Select drivers and create parties (enough to accommodate all members)
        3. Fill parties with passengers (one at a time, keeping same-time members together)
        
        Args:
            members: List of carpool members
            timetables: Timetables for all members
            start_date: Starting Monday of the cycle
            
        Returns:
            Complete driving plan
        """
        logger.info(f"=" * 80)
        logger.info(f"STARTING DRIVING PLAN CALCULATION FOR {len(members)} MEMBERS")
        logger.info(f"=" * 80)
        
        # Initialize member tracking
        self.members = {m.initials: m for m in members}
        
        # Set max drives for each member
        for member in members:
            member.max_drives = config.MAX_DRIVES_PARTTIME if member.is_part_time else config.MAX_DRIVES_FULLTIME
            member.drive_count = 0
            member.driving_days = set()  # Track which days they're driving
        
        # Track all parties globally (for filling with passengers later)
        self.all_parties: Dict[int, Dict[str, List[Party]]] = {}  # day_num -> {"schoolbound": [...], "homebound": [...]}
        for day_num in range(10):
            self.all_parties[day_num] = {"schoolbound": [], "homebound": []}
        
        # PHASE 1: Create pools
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 1: CREATE POOLS")
        logger.info("=" * 80)
        all_pools = self._create_all_pools()
        
        # PHASE 2: Select drivers and create parties
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 2: SELECT DRIVERS AND CREATE PARTIES")
        logger.info("=" * 80)
        self._select_drivers_and_create_parties(all_pools)
        
        # PHASE 3: Fill parties with passengers
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 3: FILL PARTIES WITH PASSENGERS")
        logger.info("=" * 80)
        self._fill_parties_with_passengers(all_pools)
        
        # Build final day plans
        logger.info("\n" + "=" * 80)
        logger.info("BUILDING FINAL DAY PLANS")
        logger.info("=" * 80)
        dates = get_week_dates(start_date)
        day_plans = {}
        
        for day_num, date in enumerate(dates):
            is_week_a = day_num < 5
            day_of_week = get_day_of_week_name(date)
            
            day_of_week_ab = DayOfWeekABCombo(
                day_of_week=day_of_week,
                is_week_a=is_week_a,
                unique_number=day_num + 1
            )
            
            day_plan = self._build_day_plan_from_parties(day_num, day_of_week_ab)
            day_plans[day_num + 1] = day_plan
        
        # Generate summary
        summary = self._generate_summary(members)
        
        logger.info("\n" + "=" * 80)
        logger.info("DRIVING PLAN CALCULATION COMPLETE")
        logger.info("=" * 80)
        
        return DrivingPlan(summary=summary, day_plans=day_plans)
    
    
    def _create_all_pools(self) -> List[DriverPool]:
        """
        PHASE 1: Create pools for all days, directions, and time slots.
        Sort by size in ascending order (smallest/most constrained first).
        
        Returns:
            List of driver pools sorted by size
        """
        all_pools = []
        
        for day_num in range(10):
            # Create pools for both directions
            schoolbound_pools = self._create_driver_pools(day_num, schoolbound=True)
            homebound_pools = self._create_driver_pools(day_num, schoolbound=False)
            
            all_pools.extend(schoolbound_pools)
            all_pools.extend(homebound_pools)
            
            logger.info(f"Day {day_num + 1}: Created {len(schoolbound_pools)} schoolbound pools, {len(homebound_pools)} homebound pools")
        
        # Sort by size (most constrained first)
        all_pools.sort(key=lambda p: len(p.time_slot.members))
        
        logger.info(f"\nTotal pools created: {len(all_pools)}")
        logger.info(f"Pool size distribution:")
        size_counts = defaultdict(int)
        for pool in all_pools:
            size_counts[len(pool.time_slot.members)] += 1
        for size in sorted(size_counts.keys()):
            logger.info(f"  Size {size}: {size_counts[size]} pools")
        
        return all_pools
    
    def _select_drivers_and_create_parties(self, all_pools: List[DriverPool]) -> None:
        """
        PHASE 2: Select drivers and create parties (both directions) for each pool.
        Create enough parties to accommodate all members without assigning passengers yet.
        
        Args:
            all_pools: All driver pools sorted by size
        """
        # Track who is driving on each day (to prevent them being passengers)
        drivers_by_day: Dict[int, Set[str]] = defaultdict(set)
        
        logger.info(f"\nProcessing {len(all_pools)} pools (smallest first)...")
        
        for pool_idx, pool in enumerate(all_pools):
            day_num = pool.day_num
            direction = "to school" if pool.schoolbound else "home"
            
            logger.info(f"\n--- Pool {pool_idx + 1}/{len(all_pools)}: Day {day_num + 1}, {direction}, {len(pool.time_slot.members)} members ---")
            
            # Determine how many drivers we need for this pool
            remaining_to_cover = [m for m in pool.time_slot.members if m not in drivers_by_day[day_num]]
            
            if not remaining_to_cover:
                logger.info(f"All members already driving on day {day_num + 1}, no additional drivers needed")
                continue
            
            # Select drivers until we have enough capacity
            total_capacity = 0
            drivers_selected = []
            
            while len(remaining_to_cover) > total_capacity:
                # PRIORITY 1: Check if anyone in remaining_to_cover needs a car (must drive)
                mandatory_driver = None
                for member_initials in remaining_to_cover:
                    if (member_initials in pool.candidates and 
                        member_initials not in drivers_by_day[day_num] and
                        self.members[member_initials].needs_car_on_day(day_num)):
                        mandatory_driver = member_initials
                        logger.info(f"  ! {mandatory_driver} needs car on day {day_num + 1}, must be selected as driver")
                        break
                
                if mandatory_driver:
                    driver = mandatory_driver
                else:
                    # PRIORITY 2: Normal driver selection
                    # Find available candidates (not already driving today)
                    available_candidates = [
                        c for c in pool.candidates 
                        if c not in drivers_by_day[day_num]
                        and self.members[c].drive_count < self.members[c].max_drives
                    ]
                    
                    # If no one available within max drives, allow exceeding
                    if not available_candidates:
                        available_candidates = [
                            c for c in pool.candidates 
                            if c not in drivers_by_day[day_num]
                        ]
                    
                    if not available_candidates:
                        logger.warning(f"Cannot find driver for pool on day {day_num + 1} {direction}")
                        break
                    
                    # Select best driver
                    driver = self._select_best_driver(available_candidates, all_pools, pool)
                drivers_selected.append(driver)
                
                # Mark as driver for this day
                drivers_by_day[day_num].add(driver)
                
                # Update capacity
                driver_capacity = self.members[driver].number_of_seats - 1
                total_capacity += driver_capacity
                
                # Remove driver from remaining
                if driver in remaining_to_cover:
                    remaining_to_cover.remove(driver)
                
                # Update drive count if not already driving this day
                if day_num not in self.members[driver].driving_days:
                    self.members[driver].drive_count += 1
                    self.members[driver].driving_days.add(day_num)
                
                # Get times for this driver
                driver_timetable = self.members[driver].timetable.get(day_num)
                custom_day = self.members[driver].get_custom_day(day_num)
                
                # Get schoolbound time (custom start takes priority)
                schoolbound_time = None
                if custom_day and custom_day.custom_start:
                    # Parse custom_start (HH:MM format) to HHMM integer
                    schoolbound_time = int(custom_day.custom_start.replace(':', ''))
                elif driver_timetable:
                    schoolbound_time = driver_timetable.get_start_time()
                
                # Get homebound time (custom end takes priority)
                homebound_time = None
                if custom_day and custom_day.custom_end:
                    # Parse custom_end (HH:MM format) to HHMM integer
                    homebound_time = int(custom_day.custom_end.replace(':', ''))
                elif driver_timetable:
                    homebound_time = driver_timetable.get_end_time()
                
                # Skip this driver if no valid times available
                if schoolbound_time is None or homebound_time is None:
                    print(f"  ⚠️ Skipping {driver}: No valid times (schoolbound={schoolbound_time}, homebound={homebound_time})")
                    continue
                
                is_mandatory = len(pool.candidates) == 1
                
                # Create TWO parties for this driver (both directions)
                schoolbound_party = Party(
                    day_of_week_ab_combo=None,  # Will be set later
                    driver=driver,
                    time=schoolbound_time,
                    passengers=[],  # Empty for now
                    is_designated_driver=is_mandatory,
                    drives_despite_custom_prefs=False,
                    schoolbound=True
                )
                
                homebound_party = Party(
                    day_of_week_ab_combo=None,  # Will be set later
                    driver=driver,
                    time=homebound_time,
                    passengers=[],  # Empty for now
                    is_designated_driver=is_mandatory,
                    drives_despite_custom_prefs=False,
                    schoolbound=False
                )
                
                # Add parties to global tracking
                self.all_parties[day_num]["schoolbound"].append(schoolbound_party)
                self.all_parties[day_num]["homebound"].append(homebound_party)
                
                # Determine reason for selection
                reason = self._get_selection_reason(driver, available_candidates)
                
                logger.info(f"✓ Selected {driver} as driver for day {day_num + 1}")
                logger.info(f"  - Schoolbound time: {schoolbound_time}")
                logger.info(f"  - Homebound time: {homebound_time}")
                logger.info(f"  - Reason: {reason}")
                logger.info(f"  - Total driving days: {len(self.members[driver].driving_days)}")
                logger.info(f"  - Remaining to cover: {len(remaining_to_cover)} members")
            
            logger.info(f"Pool complete: {len(drivers_selected)} drivers selected, capacity for {total_capacity} passengers")
    
    def _fill_parties_with_passengers(self, all_pools: List[DriverPool]) -> None:
        """
        PHASE 3: Fill parties with passengers one at a time.
        Keep same-time members together, balance passengers among parties.
        
        Args:
            all_pools: All driver pools
        """
        logger.info(f"\nFilling parties with passengers...")
        
        for day_num in range(10):
            for direction_key in ["schoolbound", "homebound"]:
                schoolbound = (direction_key == "schoolbound")
                direction = "to school" if schoolbound else "home"
                parties = self.all_parties[day_num][direction_key]
                
                if not parties:
                    continue
                
                logger.info(f"\n--- Day {day_num + 1}, {direction}: {len(parties)} parties ---")
                
                # Get all drivers for this day/direction
                drivers = {party.driver for party in parties}
                
                # Find all members who need rides (not drivers)
                pools_for_direction = [p for p in all_pools if p.day_num == day_num and p.schoolbound == schoolbound]
                all_members_needing_rides = set()
                for pool in pools_for_direction:
                    all_members_needing_rides.update(pool.time_slot.members)
                
                passengers_to_assign = [m for m in all_members_needing_rides if m not in drivers]
                
                # Group passengers by their actual time (to keep same-time members together)
                passengers_by_time = defaultdict(list)
                for passenger in passengers_to_assign:
                    passenger_timetable = self.members[passenger].timetable.get(day_num)
                    if passenger_timetable:
                        time = passenger_timetable.get_start_time() if schoolbound else passenger_timetable.get_end_time()
                        passengers_by_time[time].append(passenger)
                
                # Assign passengers one at a time, grouped by time
                for time in sorted(passengers_by_time.keys()):
                    time_group = passengers_by_time[time]
                    logger.info(f"\nAssigning {len(time_group)} passengers with time {time}")
                    
                    for passenger in time_group:
                        # Find best party for this passenger
                        best_party = self._find_best_party_for_passenger(parties, passenger, time)
                        
                        if best_party:
                            party_time_before = best_party.time
                            best_party.passengers.append(passenger)
                            
                            # Update party time dynamically
                            all_member_times = []
                            for member in [best_party.driver] + best_party.passengers:
                                member_timetable = self.members[member].timetable.get(day_num)
                                if member_timetable:
                                    member_time = member_timetable.get_start_time() if schoolbound else member_timetable.get_end_time()
                                    if member_time:
                                        all_member_times.append(member_time)
                            
                            if all_member_times:
                                best_party.time = get_earliest_time(all_member_times) if schoolbound else get_latest_time(all_member_times)
                            
                            logger.info(f"  ✓ Added {passenger} to {best_party.driver}'s party")
                            logger.info(f"    - Party time before: {party_time_before}")
                            logger.info(f"    - Passenger time: {time}")
                            logger.info(f"    - Party time after: {best_party.time}")
                        else:
                            logger.warning(f"  ! Could not find party for passenger {passenger}")
    
    def _select_best_driver(self, candidates: List[str], all_pools: List[DriverPool], current_pool: DriverPool) -> str:
        """
        Select the best driver from candidates based on drive count, capacity, and future needs.
        
        Args:
            candidates: Available candidates
            all_pools: All pools
            current_pool: Current pool being processed
            
        Returns:
            Selected driver initials
        """
        if len(candidates) == 1:
            return candidates[0]
        
        # Score each candidate
        candidate_scores = []
        
        for candidate in candidates:
            member = self.members[candidate]
            
            # Count future mandatory pools where this person is the only candidate
            future_mandatory_count = 0
            for pool in all_pools:
                if pool.day_num < current_pool.day_num:
                    continue
                if pool == current_pool:
                    continue
                if len(pool.candidates) == 1 and pool.candidates[0] == candidate:
                    future_mandatory_count += 1
            
            # Scoring (lower is better)
            score = (
                -future_mandatory_count * 100,  # Save them if they have mandatory drives later
                member.drive_count,  # Prefer those who haven't driven much
                -member.number_of_seats  # Prefer larger capacity
            )
            
            candidate_scores.append((score, candidate))
        
        candidate_scores.sort()
        return candidate_scores[0][1]
    
    def _get_selection_reason(self, driver: str, candidates: List[str]) -> str:
        """
        Get the reason why a driver was selected.
        
        Args:
            driver: Selected driver
            candidates: All candidates
            
        Returns:
            Reason string
        """
        if len(candidates) == 1:
            return "Only candidate available"
        
        member = self.members[driver]
        reasons = []
        
        if member.drive_count == min(self.members[c].drive_count for c in candidates):
            reasons.append("lowest drive count")
        
        if member.number_of_seats == max(self.members[c].number_of_seats for c in candidates):
            reasons.append("highest capacity")
        
        return ", ".join(reasons) if reasons else "balanced selection"
    
    def _find_best_party_for_passenger(self, parties: List[Party], passenger: str, passenger_time: int) -> Optional[Party]:
        """
        Find the best party for a passenger, preferring parties with same time and available space.
        
        Args:
            parties: Available parties
            passenger: Passenger initials
            passenger_time: Passenger's time
            
        Returns:
            Best party or None
        """
        # Filter parties with available space
        available_parties = [
            p for p in parties 
            if len(p.passengers) < (self.members[p.driver].number_of_seats - 1)
        ]
        
        if not available_parties:
            return None
        
        # First priority: parties with the exact same time
        same_time_parties = [p for p in available_parties if abs(p.time - passenger_time) < 5]
        if same_time_parties:
            # Among same-time parties, pick the one with most passengers already (fill up existing parties first)
            return max(same_time_parties, key=lambda p: len(p.passengers))
        
        # Second priority: parties with time within tolerance
        within_tolerance_parties = [
            p for p in available_parties 
            if times_within_tolerance(p.time, passenger_time, self.tolerance)
        ]
        if within_tolerance_parties:
            # Pick the one with fewest passengers (balance across parties)
            return min(within_tolerance_parties, key=lambda p: len(p.passengers))
        
        # Last resort: any party with space
        return min(available_parties, key=lambda p: len(p.passengers))
    
    def _build_day_plan_from_parties(self, day_num: int, day_of_week_ab: DayOfWeekABCombo) -> DayPlan:
        """
        Build a day plan from the parties created for this day.
        Includes validation to ensure consistency.
        
        Args:
            day_num: Day number (0-9)
            day_of_week_ab: Day identifier
            
        Returns:
            DayPlan for this day
        """
        parties = []
        schoolbound_times = {}
        homebound_times = {}
        
        # Collect all parties for this day
        for schoolbound_party in self.all_parties[day_num]["schoolbound"]:
            schoolbound_party.day_of_week_ab_combo = day_of_week_ab
            parties.append(schoolbound_party)
            
            # Record times
            schoolbound_times[schoolbound_party.driver] = schoolbound_party.time
            for passenger in schoolbound_party.passengers:
                passenger_timetable = self.members[passenger].timetable.get(day_num)
                if passenger_timetable:
                    schoolbound_times[passenger] = passenger_timetable.get_start_time()
        
        for homebound_party in self.all_parties[day_num]["homebound"]:
            homebound_party.day_of_week_ab_combo = day_of_week_ab
            parties.append(homebound_party)
            
            # Record times
            homebound_times[homebound_party.driver] = homebound_party.time
            for passenger in homebound_party.passengers:
                passenger_timetable = self.members[passenger].timetable.get(day_num)
                if passenger_timetable:
                    homebound_times[passenger] = passenger_timetable.get_end_time()
        
        # VALIDATION 1: Check that no one is both driver and passenger
        logger.info(f"\nValidating day {day_num + 1}...")
        
        drivers_on_day = set()
        passengers_on_day = set()
        
        for party in parties:
            drivers_on_day.add(party.driver)
            passengers_on_day.update(party.passengers)
        
        driver_and_passenger = drivers_on_day & passengers_on_day
        if driver_and_passenger:
            error_msg = f"VALIDATION ERROR on day {day_num + 1}: Members are both driver and passenger: {driver_and_passenger}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # VALIDATION 2: Check that all expected members appear in the day plan
        all_members_in_parties = drivers_on_day | passengers_on_day
        
        members_schoolbound = set()
        members_homebound = set()
        
        for party in parties:
            if party.schoolbound:
                members_schoolbound.add(party.driver)
                members_schoolbound.update(party.passengers)
            else:
                members_homebound.add(party.driver)
                members_homebound.update(party.passengers)
        
        missing_members = []
        for initials, member in self.members.items():
            # Check if member should be present this day
            timetable = member.timetable.get(day_num)
            
            # Skip if member should be ignored (day off or custom setting)
            if member.should_ignore_on_day(day_num):
                continue
            
            if not timetable or not timetable.is_present:
                continue
            
            # Check if member appears in expected directions
            has_morning = timetable.get_start_time() is not None
            has_afternoon = timetable.get_end_time() is not None
            
            if has_morning and initials not in members_schoolbound:
                missing_members.append(f"{initials} (schoolbound)")
            
            if has_afternoon and initials not in members_homebound:
                missing_members.append(f"{initials} (homebound)")
        
        if missing_members:
            error_msg = f"VALIDATION ERROR on day {day_num + 1}: Members missing from day plan: {missing_members}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"✓ Day {day_num + 1} validation passed")
        
        return DayPlan(
            day_of_week_ab_combo=day_of_week_ab,
            parties=parties,
            schoolbound_times_by_initials=schoolbound_times,
            homebound_times_by_initials=homebound_times
        )
    
    def _create_driver_pools(self, day_num: int, schoolbound: bool) -> List[DriverPool]:
        """
        Create driver candidate pools for a day and direction.
        
        Args:
            day_num: Day number (0-9)
            schoolbound: True for morning, False for afternoon
            
        Returns:
            List of driver pools
        """
        # Group members by time slots
        time_slots = self._group_members_by_time(day_num, schoolbound)
        
        # Create driver pools
        pools = []
        for time_slot in time_slots:
            pool = DriverPool(time_slot, day_num, schoolbound)
            
            # Determine who can drive
            for initials in time_slot.members:
                member = self.members[initials]
                member_timetable = member.timetable.get(day_num)
                
                # Check if member can drive (has schedule, not ignore_completely)
                # Note: needs_car_on_day means they MUST drive, not that they can't drive
                if member.can_drive_on_day(day_num, member_timetable):
                    pool.candidates.append(initials)
            
            # If no one can drive, find someone who can exceed constraints
            if not pool.candidates:
                for initials in time_slot.members:
                    member = self.members[initials]
                    member_timetable = member.timetable.get(day_num)
                    if member.can_drive_on_day(day_num, member_timetable):
                        pool.candidates.append(initials)
                        break
            
            if pool.candidates:  # Only add pools with potential drivers
                pools.append(pool)
        
        return pools
    
    def _group_members_by_time(self, day_num: int, schoolbound: bool) -> List[TimeSlot]:
        """
        Group members into time slots based on their schedules.
        
        Args:
            day_num: Day number (0-9)
            schoolbound: True for morning, False for afternoon
            
        Returns:
            List of time slots with members
        """
        time_groups = defaultdict(lambda: TimeSlot(0, schoolbound))
        
        for initials, member in self.members.items():
            timetable = member.timetable.get(day_num)
            custom_day = member.get_custom_day(day_num)
            
            # Check if member should be ignored
            if member.should_ignore_on_day(day_num, timetable):
                continue
            
            # Get the relevant time from custom prefs or timetable
            time = None
            if schoolbound:
                if custom_day and custom_day.custom_start:
                    time = int(custom_day.custom_start.replace(':', ''))
                elif timetable:
                    time = timetable.get_start_time()
            else:
                if custom_day and custom_day.custom_end:
                    time = int(custom_day.custom_end.replace(':', ''))
                elif timetable:
                    time = timetable.get_end_time()
            
            if time is None:
                continue
            
            # Find or create a time slot within tolerance
            found_slot = False
            for existing_time, slot in time_groups.items():
                if times_within_tolerance(time, existing_time, self.tolerance):
                    slot.add_member(initials)
                    found_slot = True
                    break
            
            if not found_slot:
                slot = TimeSlot(time, schoolbound)
                slot.add_member(initials)
                time_groups[time] = slot
        
        return list(time_groups.values())
    
    def _generate_summary(self, members: List[Member]) -> str:
        """
        Generate a summary of the driving plan.
        
        Args:
            members: List of members
            
        Returns:
            Summary string
        """
        lines = []
        
        # Sort members by drive count (descending) then by name
        sorted_members = sorted(
            members,
            key=lambda m: (-m.drive_count, m.last_name, m.first_name)
        )
        
        for member in sorted_members:
            lines.append(f"- {member.first_name} ({member.initials}): {member.drive_count}")
        
        return "\n".join(lines) + "\n"

    
    def _build_day_plan_from_pools(
        self, 
        day_num: int, 
        day_of_week_ab: DayOfWeekABCombo,
        all_pools: List[DriverPool]
    ) -> DayPlan:
        """
        Build a day plan from assigned driver pools.
        
        Args:
            day_num: Day number (0-9)
            day_of_week_ab: Day identifier
            all_pools: All driver pools with assignments
            
        Returns:
            DayPlan for this day
        """
        # Filter pools for this day
        day_pools = [p for p in all_pools if p.day_num == day_num and p.is_fully_assigned]
        
        parties = []
        schoolbound_times = {}
        homebound_times = {}
        
        for pool in day_pools:
            # Create parties from all assignments (one pool can have multiple parties)
            for driver, passengers in pool.assignments:
                party, times = self._create_party_from_assignment(
                    driver, passengers, pool, day_of_week_ab, all_pools
                )
                parties.append(party)
                
                if pool.schoolbound:
                    schoolbound_times.update(times)
                else:
                    homebound_times.update(times)
        
        # VALIDATION: Check that no one is both driver and passenger on same day
        drivers_on_day = set()
        passengers_on_day = set()
        
        for party in parties:
            drivers_on_day.add(party.driver)
            passengers_on_day.update(party.passengers)
        
        # Find any overlap
        driver_and_passenger = drivers_on_day & passengers_on_day
        if driver_and_passenger:
            error_msg = f"VALIDATION ERROR on day {day_num + 1}: Members are both driver and passenger: {driver_and_passenger}"
            logger.error(error_msg)
            # Log details for debugging
            for initials in driver_and_passenger:
                driver_parties = [p for p in parties if p.driver == initials]
                passenger_parties = [p for p in parties if initials in p.passengers]
                logger.error(f"  {initials} drives in: {['schoolbound' if p.schoolbound else 'homebound' for p in driver_parties]}")
                logger.error(f"  {initials} is passenger in: {['schoolbound' if p.schoolbound else 'homebound' for p in passenger_parties]}")
            raise ValueError(error_msg)
        
        # VALIDATION: Check that all expected members appear in the day plan
        all_members_in_parties = drivers_on_day | passengers_on_day
        
        # Get schoolbound and homebound parties
        schoolbound_parties = [p for p in parties if p.schoolbound]
        homebound_parties = [p for p in parties if not p.schoolbound]
        
        members_schoolbound = set()
        members_homebound = set()
        
        for party in schoolbound_parties:
            members_schoolbound.add(party.driver)
            members_schoolbound.update(party.passengers)
        
        for party in homebound_parties:
            members_homebound.add(party.driver)
            members_homebound.update(party.passengers)
        
        # Check each member
        missing_members = []
        for initials, member in self.members.items():
            # Check if member should be present this day
            timetable = member.timetable.get(day_num)
            
            # Skip if no timetable or not present (day off)
            if not timetable or not timetable.is_present:
                continue
            
            # Skip if member has custom day with ignore_completely
            custom_day = member.get_custom_day(day_num)
            if custom_day and custom_day.ignore_completely:
                continue
            
            # Check if member appears in both directions (or at least in directions they should)
            has_morning = timetable.get_start_time() is not None
            has_afternoon = timetable.get_end_time() is not None
            
            # If member should have morning, check schoolbound
            if has_morning and initials not in members_schoolbound:
                missing_members.append(f"{initials} (schoolbound)")
            
            # If member should have afternoon, check homebound
            if has_afternoon and initials not in members_homebound:
                missing_members.append(f"{initials} (homebound)")
        
        if missing_members:
            error_msg = f"VALIDATION ERROR on day {day_num + 1}: Members missing from day plan: {missing_members}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        return DayPlan(
            day_of_week_ab_combo=day_of_week_ab,
            parties=parties,
            schoolbound_times_by_initials=schoolbound_times,
            homebound_times_by_initials=homebound_times
        )
    
    def _create_party_from_assignment(
        self,
        driver: str,
        passengers: List[str],
        pool: DriverPool,
        day_of_week_ab: DayOfWeekABCombo,
        all_pools: List[DriverPool]
    ) -> Tuple[Party, Dict[str, int]]:
        """
        Create a party from a driver assignment.
        
        Args:
            driver: Driver initials
            passengers: List of passenger initials
            pool: Driver pool this assignment belongs to
            day_of_week_ab: Day identifier
            all_pools: All driver pools (to check opposite direction)
            
        Returns:
            Tuple of (party, dict of times by initials)
        """
        times = {}
        all_initials = [driver] + passengers
        party_times = []
        
        # Collect times for all participants
        for initials in all_initials:
            timetable = self.members[initials].timetable.get(pool.day_num)
            if timetable:
                time = timetable.get_start_time() if pool.schoolbound else timetable.get_end_time()
                if time:
                    party_times.append(time)
                    times[initials] = time
        
        # Party time is earliest for schoolbound, latest for homebound
        party_time = get_earliest_time(party_times) if pool.schoolbound else get_latest_time(party_times)
        
        # Check if this is a mandatory driver
        # Mandatory if: this pool is mandatory OR opposite direction pool with same driver is mandatory
        is_mandatory = pool.is_mandatory
        if not is_mandatory:
            # Check opposite direction pools for this driver on same day
            opposite_direction = not pool.schoolbound
            for other_pool in all_pools:
                if (other_pool.day_num == pool.day_num and 
                    other_pool.schoolbound == opposite_direction and
                    driver in other_pool.time_slot.members):
                    # Check if this driver has a mandatory assignment in opposite direction
                    for assigned_driver, _ in other_pool.assignments:
                        if assigned_driver == driver and other_pool.is_mandatory:
                            is_mandatory = True
                            break
                    if is_mandatory:
                        break
        
        party = Party(
            day_of_week_ab_combo=day_of_week_ab,
            driver=driver,
            time=party_time or 800,  # Default time if none found
            passengers=passengers,
            is_designated_driver=is_mandatory,
            drives_despite_custom_prefs=False,
            schoolbound=pool.schoolbound
        )
        
        return party, times
    
    def _calculate_day_plan(self, day_num: int, day_of_week_ab: DayOfWeekABCombo) -> DayPlan:
        """
        Calculate the driving plan for a single day.
        
        Args:
            day_num: Day number (0-9)
            day_of_week_ab: Day identifier
            
        Returns:
            DayPlan for this day
        """
        logger.info(f"Calculating plan for day {day_num + 1} ({day_of_week_ab.day_of_week})")
        
        # Collect time slots and driver pools
        schoolbound_pools = self._create_driver_pools(day_num, schoolbound=True)
        homebound_pools = self._create_driver_pools(day_num, schoolbound=False)
        
        # Create parties
        parties = []
        schoolbound_times = {}
        homebound_times = {}
        
        # Process schoolbound journey
        for pool in schoolbound_pools:
            party_list, times = self._create_parties_for_pool(pool, day_of_week_ab, True)
            parties.extend(party_list)
            schoolbound_times.update(times)
        
        # Process homebound journey
        for pool in homebound_pools:
            party_list, times = self._create_parties_for_pool(pool, day_of_week_ab, False)
            parties.extend(party_list)
            homebound_times.update(times)
        
        return DayPlan(
            day_of_week_ab_combo=day_of_week_ab,
            parties=parties,
            schoolbound_times_by_initials=schoolbound_times,
            homebound_times_by_initials=homebound_times
        )
    
    def _create_driver_pools(self, day_num: int, schoolbound: bool) -> List[DriverPool]:
        """
        Create driver candidate pools for a day and direction.
        
        Args:
            day_num: Day number (0-9)
            schoolbound: True for morning, False for afternoon
            
        Returns:
            List of driver pools sorted by size (mandatory first)
        """
        # Group members by time slots
        time_slots = self._group_members_by_time(day_num, schoolbound)
        
        # Create driver pools
        pools = []
        for time_slot in time_slots:
            pool = DriverPool(time_slot, day_num, schoolbound)
            
            # Determine who can drive and who needs rides
            for initials in time_slot.members:
                member = self.members[initials]
                
                if member.can_drive_on_day(day_num):
                    # Add as potential driver (don't check drive_count yet)
                    pool.candidates.append(initials)
                else:
                    # Member needs a ride
                    pool.passengers.append(initials)
            
            # If no one can drive, we need to find someone who exceeds max drives
            if not pool.candidates and pool.passengers:
                # Find the member with the most capacity or who can exceed
                for initials in pool.passengers[:]:
                    member = self.members[initials]
                    if member.can_drive_on_day(day_num):
                        pool.candidates.append(initials)
                        pool.passengers.remove(initials)
                        break
            
            if pool.candidates:  # Only add pools that have potential drivers
                pools.append(pool)
        
        # Sort by pool size (mandatory drivers first)
        pools.sort(key=lambda p: p.size)
        return pools
    
    def _group_members_by_time(self, day_num: int, schoolbound: bool) -> List[TimeSlot]:
        """
        Group members into time slots based on their schedules.
        
        Args:
            day_num: Day number (0-9)
            schoolbound: True for morning, False for afternoon
            
        Returns:
            List of time slots with members
        """
        time_groups = defaultdict(lambda: TimeSlot(0, schoolbound))
        
        for initials in self.members:
            member = self.members[initials]
            timetable = member.timetable.get(day_num)
            
            if not timetable or not timetable.is_present:
                continue
            
            # Get the relevant time
            time = timetable.get_start_time() if schoolbound else timetable.get_end_time()
            
            if time is None:
                continue
            
            # Find or create a time slot within tolerance
            found_slot = False
            for existing_time, slot in time_groups.items():
                if times_within_tolerance(time, existing_time, self.tolerance):
                    slot.add_member(initials)
                    found_slot = True
                    break
            
            if not found_slot:
                slot = TimeSlot(time, schoolbound)
                slot.add_member(initials)
                time_groups[time] = slot
        
        return list(time_groups.values())
    
    def _create_parties_for_pool(
        self, 
        pool: DriverPool, 
        day_of_week_ab: DayOfWeekABCombo,
        schoolbound: bool
    ) -> Tuple[List[Party], Dict[str, int]]:
        """
        Create parties for a driver pool.
        
        Args:
            pool: Driver pool
            day_of_week_ab: Day identifier
            schoolbound: Direction
            
        Returns:
            Tuple of (list of parties, dict of times by initials)
        """
        parties = []
        times = {}
        
        # Choose driver(s)
        if pool.is_mandatory:
            # Mandatory driver - only one option
            driver_initials = pool.candidates[0]
            drivers = [driver_initials]
        else:
            # Choose optimal driver(s) based on capacity and balance
            drivers = self._select_optimal_drivers(pool)
        
        # Determine party time (earliest for schoolbound, latest for homebound)
        all_initials = drivers + pool.passengers
        party_times = []
        
        for initials in all_initials:
            timetable = self.members[initials].timetable[pool.day_num]
            time = timetable.get_start_time() if schoolbound else timetable.get_end_time()
            if time:
                party_times.append(time)
                times[initials] = time
        
        party_time = get_earliest_time(party_times) if schoolbound else get_latest_time(party_times)
        
        # Create parties
        for driver_initials in drivers:
            # Distribute passengers among drivers
            passenger_list = self._distribute_passengers(drivers, pool.passengers, driver_initials)
            
            # Increment drive count
            member = self.members[driver_initials]
            member.drive_count += 1
            
            party = Party(
                day_of_week_ab_combo=day_of_week_ab,
                driver=driver_initials,
                time=party_time or 800,  # Default time if none found
                passengers=passenger_list,
                is_designated_driver=pool.is_mandatory,
                drives_despite_custom_prefs=False,
                schoolbound=schoolbound
            )
            parties.append(party)
        
        return parties, times
    
    def _select_optimal_drivers(self, pool: DriverPool) -> List[str]:
        """
        Select optimal driver(s) from a pool of candidates.
        
        Args:
            pool: Driver pool
            
        Returns:
            List of selected driver initials
        """
        # Calculate how many drivers we need
        total_passengers = len(pool.passengers)
        
        if total_passengers == 0:
            # Just pick one driver for solo journey
            return self._pick_driver_by_capacity(pool.candidates[:1])
        
        # Try to fit everyone with minimum drivers
        candidates_by_capacity = sorted(
            pool.candidates,
            key=lambda i: (self.members[i].drive_count, -self.members[i].number_of_seats)
        )
        
        drivers = []
        remaining_passengers = total_passengers
        
        for candidate in candidates_by_capacity:
            if remaining_passengers <= 0:
                break
            
            member = self.members[candidate]
            capacity = member.number_of_seats - 1  # -1 for driver
            
            if capacity > 0:
                drivers.append(candidate)
                remaining_passengers -= capacity
        
        return drivers if drivers else [candidates_by_capacity[0]]
    
    def _pick_driver_by_capacity(self, candidates: List[str]) -> List[str]:
        """Pick the best driver based on remaining capacity."""
        if not candidates:
            return []
        
        # Sort by drive count (ascending) then by seats (descending)
        best = min(
            candidates,
            key=lambda i: (self.members[i].drive_count, -self.members[i].number_of_seats)
        )
        return [best]
    
    def _distribute_passengers(
        self, 
        all_drivers: List[str], 
        all_passengers: List[str],
        current_driver: str
    ) -> List[str]:
        """
        Distribute passengers among drivers.
        
        Args:
            all_drivers: All drivers for this time slot
            all_passengers: All passengers needing rides
            current_driver: The driver we're assigning passengers to
            
        Returns:
            List of passenger initials for this driver
        """
        if not all_passengers:
            return []
        
        # Simple distribution: divide passengers evenly
        driver_index = all_drivers.index(current_driver)
        passengers_per_driver = len(all_passengers) // len(all_drivers)
        extra = len(all_passengers) % len(all_drivers)
        
        start_idx = driver_index * passengers_per_driver + min(driver_index, extra)
        end_idx = start_idx + passengers_per_driver + (1 if driver_index < extra else 0)
        
        return all_passengers[start_idx:end_idx]
    
    def _generate_summary(self, members: List[Member]) -> str:
        """
        Generate a summary of the driving plan.
        
        Args:
            members: List of members
            
        Returns:
            Summary string
        """
        lines = []
        
        # Sort members by drive count (descending) then by name
        sorted_members = sorted(
            members,
            key=lambda m: (-m.drive_count, m.last_name, m.first_name)
        )
        
        for member in sorted_members:
            lines.append(f"- {member.first_name} ({member.initials}): {member.drive_count}")
        
        return "\n".join(lines) + "\n"
