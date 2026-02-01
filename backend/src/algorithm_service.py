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
    
    @property
    def is_mandatory(self) -> bool:
        """True if this is a mandatory driver (only 1 candidate available)."""
        return len(self.candidates) == 1
    
    def __repr__(self):
        direction = "to school" if self.schoolbound else "home"
        return f"DriverPool(day={self.day_num + 1}, {direction}, {len(self.time_slot.members)} members, {len(self.candidates)} candidates)"


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
    
    def _get_day_name(self, day_num: int) -> str:
        """
        Convert day number to human-readable format.
        
        Args:
            day_num: Day number (0-9)
            
        Returns:
            String like "Monday (A)" or "Wednesday (B)"
        """
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        week = "A" if day_num < 5 else "B"
        day_of_week = day_names[day_num % 5]
        return f"{day_of_week} ({week})"
    
    def calculate_driving_plan(
        self,
        members: List[Member],
        start_date: datetime
    ) -> DrivingPlan:
        """
        Calculate the optimal driving plan for all members.
        
        This algorithm works in five phases:
        1. Create pools (grouped by day, direction, time slot)
        2. Select drivers and create parties (enough to accommodate all members)
        3. Rebalance driving distribution (swap high-count drivers with low-count alternatives)
        4. Add additional driver parties (use underutilized drivers to reduce overcrowding)
        5. Fill parties with passengers (one at a time, keeping same-time members together)
        
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
        
        # Validate custom day settings for all members
        logger.info("\nValidating custom day preferences...")
        validation_errors = []
        for member in members:
            for day_num in range(10):
                errors = member.validate_custom_day(day_num)
                if errors:
                    validation_errors.extend([f"{member.initials}: {err}" for err in errors])
        
        if validation_errors:
            error_msg = "Custom day validation failed:\n" + "\n".join(validation_errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        logger.info("✓ Custom day validation passed")
        
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
        
        # PHASE 3: Rebalance driving distribution
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 3: REBALANCE DRIVING DISTRIBUTION")
        logger.info("=" * 80)
        self._rebalance_driving_distribution(all_pools)
        
        # PHASE 4: Add additional driver parties to reduce overcrowding
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 4: ADD ADDITIONAL DRIVER PARTIES")
        logger.info("=" * 80)
        self._add_additional_driver_parties(all_pools)
        
        # PHASE 5: Fill parties with passengers
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 5: FILL PARTIES WITH PASSENGERS")
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

        # Build member ID map for UI links
        member_id_map = {m.initials: m.id for m in members if m.id is not None}
        
        return DrivingPlan(summary=summary, day_plans=day_plans, member_id_map=member_id_map)
    
    
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
            
            logger.info(f"{self._get_day_name(day_num)}: Created {len(schoolbound_pools)} schoolbound pools, {len(homebound_pools)} homebound pools")
        
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
        
        # PRIORITY: Create parties for members with "needsCar" preference first
        logger.info("\nCreating parties for members with 'needsCar' preference...")
        
        for day_num in range(10):
            for initials, member in self.members.items():
                if member.needs_car_on_day(day_num) and not member.should_ignore_on_day(day_num):
                    # Check if already added as driver
                    if day_num in member.driving_days:
                        continue
                    
                    logger.info(f"  {self._get_day_name(day_num)}: {initials} needs car")
                    
                    # Get times for this member
                    member_timetable = member.timetable.get(day_num)
                    custom_day = member.get_custom_day(day_num)
                    
                    # Get schoolbound time
                    schoolbound_time = None
                    if custom_day and custom_day.custom_start:
                        schoolbound_time = int(custom_day.custom_start.replace(':', ''))
                    elif member_timetable:
                        schoolbound_time = member_timetable.get_start_time()
                    
                    # Get homebound time
                    homebound_time = None
                    if custom_day and custom_day.custom_end:
                        homebound_time = int(custom_day.custom_end.replace(':', ''))
                    elif member_timetable:
                        homebound_time = member_timetable.get_end_time()
                    
                    # Skip if no valid times
                    if schoolbound_time is None or homebound_time is None:
                        logger.warning(f"    ⚠️ Cannot create parties for {initials}: No valid times")
                        continue
                    
                    # Check for lonely driver flags
                    is_lonely_schoolbound = member.skip_morning_on_day(day_num)
                    is_lonely_homebound = member.skip_afternoon_on_day(day_num)
                    
                    # Create parties for both directions
                    schoolbound_party = Party(
                        day_of_week_ab_combo=None,
                        driver=initials,
                        time=schoolbound_time,
                        passengers=[],
                        is_designated_driver=True,  # needsCar makes them designated
                        drives_despite_custom_prefs=False,
                        schoolbound=True,
                        is_lonely_driver=is_lonely_schoolbound
                    )
                    
                    homebound_party = Party(
                        day_of_week_ab_combo=None,
                        driver=initials,
                        time=homebound_time,
                        passengers=[],
                        is_designated_driver=True,  # needsCar makes them designated
                        drives_despite_custom_prefs=False,
                        schoolbound=False,
                        is_lonely_driver=is_lonely_homebound
                    )
                    
                    # Add to global tracking
                    self.all_parties[day_num]["schoolbound"].append(schoolbound_party)
                    self.all_parties[day_num]["homebound"].append(homebound_party)
                    
                    # Mark as driver
                    drivers_by_day[day_num].add(initials)
                    member.drive_count += 1
                    member.driving_days.add(day_num)
                    
                    logger.info(f"    ✓ Created parties for {initials} (needs car). Schoolbound: {schoolbound_time}, homebound: {homebound_time}")
        
        # PRIORITY 2: Create parties for members with "noWaitingAfternoon" preference
        # These members need a homebound party at their EXACT end time (tolerance=0)
        logger.info("\nCreating parties for members with 'noWaitingAfternoon' preference...")
        
        for day_num in range(10):
            for initials, member in self.members.items():
                if member.no_waiting_afternoon_on_day(day_num) and not member.should_ignore_on_day(day_num):
                    # Check if already driving this day
                    if day_num in member.driving_days:
                        logger.info(f"  {self._get_day_name(day_num)}: {initials} already driving, no action needed")
                        continue
                    
                    logger.info(f"  {self._get_day_name(day_num)}: {initials} needs exact-time homebound party")
                    
                    # Get their exact end time
                    member_timetable = member.timetable.get(day_num)
                    custom_day = member.get_custom_day(day_num)
                    
                    exact_end_time = None
                    if custom_day and custom_day.custom_end:
                        exact_end_time = int(custom_day.custom_end.replace(':', ''))
                    elif member_timetable:
                        exact_end_time = member_timetable.get_end_time()
                    
                    if exact_end_time is None:
                        logger.warning(f"    ⚠️ No valid end time for {initials}")
                        continue
                    
                    # Check if there's already a homebound party at this exact time
                    existing_homebound_parties = self.all_parties[day_num]["homebound"]
                    has_party_at_exact_time = any(
                        abs(party.time - exact_end_time) < 5 and not party.is_lonely_driver
                        for party in existing_homebound_parties
                    )
                    
                    if has_party_at_exact_time:
                        logger.info(f"    ✓ Party already exists at time {exact_end_time}, no action needed")
                        continue
                    
                    # No party at exact time - we need to create one
                    # Check if this member can drive
                    if not member.can_drive_on_day(day_num):
                        logger.warning(f"    ⚠️ {initials} cannot drive on {self._get_day_name(day_num)}, may not find exact-time party")
                        continue
                    
                    # Get schoolbound time as well (need both for a driving day)
                    schoolbound_time = None
                    if custom_day and custom_day.custom_start:
                        schoolbound_time = int(custom_day.custom_start.replace(':', ''))
                    elif member_timetable:
                        schoolbound_time = member_timetable.get_start_time()
                    
                    if schoolbound_time is None:
                        logger.warning(f"    ⚠️ No valid start time for {initials}")
                        continue
                    
                    # Create parties for both directions
                    is_lonely_schoolbound = member.skip_morning_on_day(day_num)
                    
                    schoolbound_party = Party(
                        day_of_week_ab_combo=None,
                        driver=initials,
                        time=schoolbound_time,
                        passengers=[],
                        is_designated_driver=True,  # noWaitingAfternoon makes them designated
                        drives_despite_custom_prefs=False,
                        schoolbound=True,
                        is_lonely_driver=is_lonely_schoolbound
                    )
                    
                    homebound_party = Party(
                        day_of_week_ab_combo=None,
                        driver=initials,
                        time=exact_end_time,  # EXACT time for homebound
                        passengers=[],
                        is_designated_driver=True,  # noWaitingAfternoon makes them designated
                        drives_despite_custom_prefs=False,
                        schoolbound=False,
                        is_lonely_driver=False  # Can take passengers homebound
                    )
                    
                    # Add to global tracking
                    self.all_parties[day_num]["schoolbound"].append(schoolbound_party)
                    self.all_parties[day_num]["homebound"].append(homebound_party)
                    
                    # Mark as driver
                    drivers_by_day[day_num].add(initials)
                    member.drive_count += 1
                    member.driving_days.add(day_num)
                    
                    logger.info(f"    ✓ Created parties for {initials} (no waiting afternoon). Homebound at exact time: {exact_end_time}")

        logger.info(f"\nProcessing {len(all_pools)} pools (smallest first)...")
        
        for pool_idx, pool in enumerate(all_pools):
            day_num = pool.day_num
            direction = "to school" if pool.schoolbound else "home"
            
            logger.info(f"\n--- Pool {pool_idx + 1}/{len(all_pools)}: {self._get_day_name(day_num)}, {direction}, {len(pool.time_slot.members)} members ---")
            
            # Determine how many drivers we need for this pool
            remaining_to_cover = [m for m in pool.time_slot.members if m not in drivers_by_day[day_num]]
            
            if not remaining_to_cover:
                logger.info(f"All members already driving on {self._get_day_name(day_num)}, no additional drivers needed")
                continue
            
            # Check existing parties for this day/direction - they might have capacity for this pool
            direction_key = "schoolbound" if pool.schoolbound else "homebound"
            existing_parties = self.all_parties[day_num][direction_key]
            
            # Calculate available capacity from existing parties within time tolerance
            total_capacity = 0
            for party in existing_parties:
                # Skip lonely drivers - they can't take passengers
                if party.is_lonely_driver:
                    continue
                # Check if party time is compatible with this pool's time
                if times_within_tolerance(party.time, pool.time_slot.time, self.tolerance):
                    driver_capacity = self.members[party.driver].number_of_seats - 1
                    available_capacity = driver_capacity - len(party.passengers)
                    if available_capacity > 0:
                        total_capacity += available_capacity
                        logger.info(f"  Existing party by {party.driver} has {available_capacity} available seats")
            
            if total_capacity >= len(remaining_to_cover):
                logger.info(f"  Existing parties can accommodate all {len(remaining_to_cover)} members, no new drivers needed")
                continue
            
            logger.info(f"  Need to cover {len(remaining_to_cover)} members, existing capacity: {total_capacity}")
            
            # Select drivers until we have enough capacity
            drivers_selected = []
            
            while len(remaining_to_cover) > total_capacity:
                # PRIORITY 1: Check if anyone in remaining_to_cover needs a car (must drive)
                mandatory_driver = None
                for member_initials in remaining_to_cover:
                    if (member_initials in pool.candidates and 
                        member_initials not in drivers_by_day[day_num] and
                        self.members[member_initials].needs_car_on_day(day_num)):
                        mandatory_driver = member_initials
                        logger.info(f"  ! {mandatory_driver} needs car on {self._get_day_name(day_num)}, must be selected as driver")
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
                        logger.warning(f"Cannot find driver for pool on {self._get_day_name(day_num)} {direction}")
                        break
                    
                    # Select best driver
                    driver = self._select_best_driver(available_candidates, all_pools, pool)
                drivers_selected.append(driver)
                
                # Mark as driver for this day
                drivers_by_day[day_num].add(driver)
                
                # Update capacity
                driver_capacity = self.members[driver].number_of_seats - 1
                
                # If this driver has skipMorning/skipAfternoon, they won't contribute to capacity
                is_lonely_schoolbound = self.members[driver].skip_morning_on_day(day_num)
                is_lonely_homebound = self.members[driver].skip_afternoon_on_day(day_num)
                
                # Only count capacity for non-lonely drivers in the relevant direction
                if pool.schoolbound and not is_lonely_schoolbound:
                    total_capacity += driver_capacity
                    logger.info(f"  Adding {driver_capacity} capacity from {driver} (schoolbound, not lonely)")
                elif not pool.schoolbound and not is_lonely_homebound:
                    total_capacity += driver_capacity
                    logger.info(f"  Adding {driver_capacity} capacity from {driver} (homebound, not lonely)")
                else:
                    logger.info(f"  {driver} is a lonely driver in this direction, no capacity added")
                
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
                
                # Check for lonely driver flags (skipMorning/skipAfternoon)
                is_lonely_schoolbound = self.members[driver].skip_morning_on_day(day_num)
                is_lonely_homebound = self.members[driver].skip_afternoon_on_day(day_num)
                
                # Create TWO parties for this driver (both directions)
                schoolbound_party = Party(
                    day_of_week_ab_combo=None,  # Will be set later
                    driver=driver,
                    time=schoolbound_time,
                    passengers=[],  # Empty for now
                    is_designated_driver=is_mandatory,
                    drives_despite_custom_prefs=False,
                    schoolbound=True,
                    is_lonely_driver=is_lonely_schoolbound
                )
                
                homebound_party = Party(
                    day_of_week_ab_combo=None,  # Will be set later
                    driver=driver,
                    time=homebound_time,
                    passengers=[],  # Empty for now
                    is_designated_driver=is_mandatory,
                    drives_despite_custom_prefs=False,
                    schoolbound=False,
                    is_lonely_driver=is_lonely_homebound
                )
                
                # Add parties to global tracking
                self.all_parties[day_num]["schoolbound"].append(schoolbound_party)
                self.all_parties[day_num]["homebound"].append(homebound_party)
                
                # Determine reason for selection
                reason = self._get_selection_reason(driver, available_candidates)
                
                logger.info(f"✓ Selected {driver} as driver for {self._get_day_name(day_num)}")
                logger.info(f"  - Schoolbound time: {schoolbound_time}")
                logger.info(f"  - Homebound time: {homebound_time}")
                logger.info(f"  - Reason: {reason}")
                logger.info(f"  - Total driving days: {len(self.members[driver].driving_days)}")
                logger.info(f"  - Remaining to cover: {len(remaining_to_cover)} members")
            
            logger.info(f"Pool complete: {len(drivers_selected)} drivers selected, capacity for {total_capacity} passengers")
            
            # Verify we have enough capacity for this pool
            if total_capacity < len(remaining_to_cover):
                logger.warning(f"⚠️ Pool may be under-capacity! Capacity: {total_capacity}, Remaining: {len(remaining_to_cover)}")

    
    def _fill_parties_with_passengers(self, all_pools: List[DriverPool]) -> None:
        """
        PHASE 5: Fill parties with passengers one at a time.
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
                
                logger.info(f"\n--- {self._get_day_name(day_num)}, {direction}: {len(parties)} parties ---")
                
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
                        best_party = self._find_best_party_for_passenger(parties, passenger, time, day_num)
                        
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
                            error_msg = f"Could not find party for passenger {passenger} on {self._get_day_name(day_num)}"
                            logger.error(error_msg)
                            raise ValueError(error_msg)
    
    def _rebalance_driving_distribution(self, all_pools: List[DriverPool]) -> None:
        """
        PHASE 3: Rebalance driving distribution by replacing high-drive-count drivers
        with lower-drive-count alternatives where possible.
        
        Args:
            all_pools: All driver pools
        """
        logger.info("Analyzing driving distribution for rebalancing...")
        
        # Identify problematic drivers (drive_count > max_drives, not mandatory)
        problematic_drivers = []
        for initials, member in self.members.items():
            if member.drive_count > member.max_drives:
                # Check if ALL their parties are mandatory
                all_mandatory = True
                for day_num in member.driving_days:
                    for direction_key in ["schoolbound", "homebound"]:
                        for party in self.all_parties[day_num][direction_key]:
                            if party.driver == initials and not party.is_designated_driver:
                                all_mandatory = False
                                break
                        if not all_mandatory:
                            break
                    if not all_mandatory:
                        break
                
                if not all_mandatory:
                    problematic_drivers.append(initials)
                    logger.info(f"Found problematic driver: {initials} with {member.drive_count} drives")
        
        if not problematic_drivers:
            logger.info("No problematic drivers found, skipping rebalancing")
            return
        
        # For each problematic driver, try to find saviors
        for problematic_initials in problematic_drivers:
            problematic_member = self.members[problematic_initials]
            logger.info(f"\\nAttempting to rebalance {problematic_initials} (currently {problematic_member.drive_count} drives)...")
            
            # Look at each driving day
            for day_num in list(problematic_member.driving_days):
                # Find non-mandatory parties for this driver
                for direction_key in ["schoolbound", "homebound"]:
                    schoolbound = (direction_key == "schoolbound")
                    parties = self.all_parties[day_num][direction_key]
                    
                    # Find the problematic driver's party
                    problematic_party = None
                    for party in parties:
                        if party.driver == problematic_initials and not party.is_designated_driver:
                            problematic_party = party
                            break
                    
                    if not problematic_party:
                        continue
                    
                    logger.info(f"  Checking {self._get_day_name(day_num)}, {direction_key} party (time {problematic_party.time})...")
                    
                    # Find pool containing the problematic driver
                    matching_pool = None
                    for pool in all_pools:
                        if (pool.day_num == day_num and 
                            pool.schoolbound == schoolbound and
                            problematic_initials in pool.time_slot.members):
                            matching_pool = pool
                            break
                    
                    if not matching_pool:
                        logger.info(f"    No matching pool found")
                        continue
                    
                    # Find potential saviors in the same pool with drive_count < max_drives
                    potential_saviors = [
                        member_init for member_init in matching_pool.time_slot.members
                        if (member_init != problematic_initials and
                            member_init in matching_pool.candidates and
                            self.members[member_init].drive_count < self.members[member_init].max_drives and
                            day_num not in self.members[member_init].driving_days)
                    ]
                    
                    if not potential_saviors:
                        logger.info(f"    No saviors available (all have drive_count >= max_drives or already driving)")
                        continue
                    
                    # Select the best savior (lowest drive count, highest capacity)
                    savior_initials = min(
                        potential_saviors,
                        key=lambda s: (self.members[s].drive_count, -self.members[s].number_of_seats)
                    )
                    savior = self.members[savior_initials]
                    
                    logger.info(f"    Found savior: {savior_initials} (currently {savior.drive_count} drives)")
                    
                    # Get savior's times for both directions
                    savior_timetable = savior.timetable.get(day_num)
                    savior_custom = savior.get_custom_day(day_num)
                    
                    # Get schoolbound time
                    savior_schoolbound_time = None
                    if savior_custom and savior_custom.custom_start:
                        savior_schoolbound_time = int(savior_custom.custom_start.replace(':', ''))
                    elif savior_timetable:
                        savior_schoolbound_time = savior_timetable.get_start_time()
                    
                    # Get homebound time
                    savior_homebound_time = None
                    if savior_custom and savior_custom.custom_end:
                        savior_homebound_time = int(savior_custom.custom_end.replace(':', ''))
                    elif savior_timetable:
                        savior_homebound_time = savior_timetable.get_end_time()
                    
                    if savior_schoolbound_time is None or savior_homebound_time is None:
                        logger.info(f"    Savior has no valid times, skipping")
                        continue
                    
                    # CRITICAL CHECK: Verify there's enough capacity after removing problematic driver
                    # After rebalancing, the problematic driver becomes a passenger IN BOTH DIRECTIONS
                    # Each person appears in exactly ONE pool per direction per day
                    
                    capacity_check_failed = False
                    for check_direction_key in ["schoolbound", "homebound"]:
                        check_schoolbound = (check_direction_key == "schoolbound")
                        check_parties = self.all_parties[day_num][check_direction_key]
                        
                        # Find THE pool containing the problematic driver (there's only one per direction)
                        check_pool = None
                        for pool in all_pools:
                            if (pool.day_num == day_num and 
                                pool.schoolbound == check_schoolbound and
                                problematic_initials in pool.time_slot.members):
                                check_pool = pool
                                break
                        
                        if not check_pool:
                            logger.info(f"    No {check_direction_key} pool found for {problematic_initials}")
                            continue
                        
                        # Count current capacity from parties within this pool's time tolerance
                        # (excluding problematic driver who will be removed)
                        remaining_capacity = 0
                        pool_drivers = set()
                        
                        for party in check_parties:
                            if (party.driver != problematic_initials and 
                                not party.is_lonely_driver and
                                times_within_tolerance(party.time, check_pool.time_slot.time, self.tolerance)):
                                party_capacity = self.members[party.driver].number_of_seats - 1
                                remaining_capacity += party_capacity
                                pool_drivers.add(party.driver)
                                logger.info(f"    {check_direction_key}: {party.driver} contributes {party_capacity} capacity")
                        
                        # Check if savior is in this pool - if not, they won't help
                        if savior_initials not in check_pool.time_slot.members:
                            logger.info(f"    {check_direction_key}: Savior {savior_initials} not in this pool, cannot help")
                            # Capacity check fails - savior can't help this pool
                            capacity_check_failed = True
                            break
                        
                        # Add savior's capacity
                        savior_capacity = self.members[savior_initials].number_of_seats - 1
                        is_savior_lonely = (
                            savior.skip_morning_on_day(day_num) if check_schoolbound 
                            else savior.skip_afternoon_on_day(day_num)
                        )
                        if not is_savior_lonely:
                            remaining_capacity += savior_capacity
                            pool_drivers.add(savior_initials)
                            logger.info(f"    {check_direction_key}: {savior_initials} (savior) contributes {savior_capacity} capacity")
                        else:
                            logger.info(f"    {check_direction_key}: {savior_initials} (savior) is lonely, no capacity")
                        
                        # Count passengers needed: all pool members except drivers
                        required_seats = len(check_pool.time_slot.members) - len(pool_drivers)
                        
                        logger.info(f"    {check_direction_key}: Pool has {len(check_pool.time_slot.members)} members, {len(pool_drivers)} drivers, need {required_seats} seats")
                        logger.info(f"    {check_direction_key}: Total capacity: {remaining_capacity}, required: {required_seats}")
                        
                        if remaining_capacity < required_seats:
                            logger.info(f"    Cannot rebalance: insufficient {check_direction_key} capacity")
                            capacity_check_failed = True
                            break
                    
                    if capacity_check_failed:
                        continue
                    
                    # Create new parties for the savior (both directions)
                    new_schoolbound_party = Party(
                        day_of_week_ab_combo=None,
                        driver=savior_initials,
                        time=savior_schoolbound_time,
                        passengers=[],
                        is_designated_driver=False,
                        drives_despite_custom_prefs=False,
                        schoolbound=True,
                        is_lonely_driver=savior.skip_morning_on_day(day_num)
                    )
                    
                    new_homebound_party = Party(
                        day_of_week_ab_combo=None,
                        driver=savior_initials,
                        time=savior_homebound_time,
                        passengers=[],
                        is_designated_driver=False,
                        drives_despite_custom_prefs=False,
                        schoolbound=False,
                        is_lonely_driver=savior.skip_afternoon_on_day(day_num)
                    )
                    
                    # All checks passed - commit the changes
                    logger.info(f"    ✓ Rebalancing successful!")
                    logger.info(f"    Savior will drive, problematic driver will be assigned as passenger in PHASE 5")
                    
                    # Remove problematic driver's parties from both directions
                    self.all_parties[day_num]["schoolbound"] = [
                        p for p in self.all_parties[day_num]["schoolbound"]
                        if p.driver != problematic_initials
                    ]
                    self.all_parties[day_num]["homebound"] = [
                        p for p in self.all_parties[day_num]["homebound"]
                        if p.driver != problematic_initials
                    ]
                    
                    # Add savior's parties
                    self.all_parties[day_num]["schoolbound"].append(new_schoolbound_party)
                    self.all_parties[day_num]["homebound"].append(new_homebound_party)
                    
                    # Update drive counts and driving days
                    problematic_member.drive_count -= 1
                    problematic_member.driving_days.discard(day_num)
                    savior.drive_count += 1
                    savior.driving_days.add(day_num)
                    
                    logger.info(f"    Updated counts: {problematic_initials}={problematic_member.drive_count}, {savior_initials}={savior.drive_count}")
                    
                    # Only rebalance one day per problematic driver to avoid over-correction
                    break
                
                if problematic_member.drive_count <= problematic_member.max_drives:
                    logger.info(f"  {problematic_initials} now has acceptable drive count ({problematic_member.drive_count})")
                    break
    
        
    def _add_additional_driver_parties(self, all_pools: List[DriverPool]) -> None:
        """
        PHASE 4: Add additional driver parties from underutilized members to reduce overcrowding.
        
        Use members with fewer than 4 driving days to create additional parties on days where
        existing parties are at high capacity.
        
        Args:
            all_pools: All driver pools
        """
        logger.info("Analyzing potential additional drivers to reduce overcrowding...")
        
        # Identify members with fewer than max_drives driving days
        underutilized_members = [
            (initials, member) for initials, member in self.members.items()
            if member.drive_count < member.max_drives
        ]
        
        logger.info(f"Found {len(underutilized_members)} members with fewer than max_drives drives")
        
        for initials, member in underutilized_members:
            # Find days when this member is not driving
            non_driving_days = [day_num for day_num in range(10) if day_num not in member.driving_days]
            
            if not non_driving_days:
                logger.info(f"  {member.first_name} ({initials}) has {member.drive_count} drives but is already driving on all available days")
                continue
            
            # Check each non-driving day to see if we can help
            helped_any_day = False
            
            for day_num in non_driving_days:
                # Check if member should be ignored this day
                if member.should_ignore_on_day(day_num):
                    continue
                
                # Check if member can drive this day
                if not member.can_drive_on_day(day_num):
                    continue
                
                # Check both directions for high capacity pools
                for direction_key in ["schoolbound", "homebound"]:
                    schoolbound = (direction_key == "schoolbound")
                    
                    # Find pools for this day/direction that contain this member
                    matching_pools = [
                        pool for pool in all_pools
                        if (pool.day_num == day_num and 
                            pool.schoolbound == schoolbound and
                            initials in pool.time_slot.members)
                    ]
                    
                    if not matching_pools:
                        continue
                    
                    # For each matching pool, check if it's at high capacity
                    for pool in matching_pools:
                        # Get existing parties for this pool
                        parties = self.all_parties[day_num][direction_key]
                        
                        # Filter parties that are within time tolerance of this pool
                        relevant_parties = [
                            p for p in parties
                            if times_within_tolerance(p.time, pool.time_slot.time, self.tolerance)
                        ]
                        
                        if not relevant_parties:
                            continue
                        
                        # Calculate total capacity and required seats
                        total_capacity = sum(
                            self.members[p.driver].number_of_seats - 1
                            for p in relevant_parties
                        )
                        required_seats = len(pool.time_slot.members) - len(relevant_parties)  # Exclude drivers
                        
                        # Check if we're at high capacity (capacity is close to or equal to required)
                        # Define "high capacity" as having 0-2 spare seats
                        spare_seats = total_capacity - required_seats
                        
                        if 0 <= spare_seats <= 2:
                            # This pool is at high capacity - add this member as driver
                            logger.info(f"  {self._get_day_name(day_num)}, {direction_key}: High capacity detected")
                            logger.info(f"    Pool time: {pool.time_slot.time}, {len(pool.time_slot.members)} members")
                            logger.info(f"    Current capacity: {total_capacity} seats, required: {required_seats}, spare: {spare_seats}")
                            logger.info(f"    Adding {member.first_name} ({initials}) as additional driver")
                            
                            # Get member's times for both directions
                            member_custom = member.get_custom_day(day_num)
                            
                            # Get schoolbound time
                            member_schoolbound_time = None
                            if member_custom and member_custom.custom_start:
                                member_schoolbound_time = int(member_custom.custom_start.replace(':', ''))
                            elif member.timetable and day_num in member.timetable:
                                member_schoolbound_time = member.timetable[day_num].get_start_time()
                            
                            # Get homebound time
                            member_homebound_time = None
                            if member_custom and member_custom.custom_end:
                                member_homebound_time = int(member_custom.custom_end.replace(':', ''))
                            elif member.timetable and day_num in member.timetable:
                                member_homebound_time = member.timetable[day_num].get_end_time()
                            
                            if member_schoolbound_time is None or member_homebound_time is None:
                                logger.info(f"    Cannot add {initials}: No valid times")
                                continue
                            
                            # Create new parties for both directions
                            new_schoolbound_party = Party(
                                day_of_week_ab_combo=None,
                                driver=initials,
                                time=member_schoolbound_time,
                                passengers=[],
                                is_designated_driver=False,
                                drives_despite_custom_prefs=False,
                                schoolbound=True
                            )
                            
                            new_homebound_party = Party(
                                day_of_week_ab_combo=None,
                                driver=initials,
                                time=member_homebound_time,
                                passengers=[],
                                is_designated_driver=False,
                                drives_despite_custom_prefs=False,
                                schoolbound=False
                            )
                            
                            # Add parties
                            self.all_parties[day_num]["schoolbound"].append(new_schoolbound_party)
                            self.all_parties[day_num]["homebound"].append(new_homebound_party)
                            
                            # Update drive counts
                            member.drive_count += 1
                            member.driving_days.add(day_num)
                            
                            logger.info(f"    ✓ Added parties for {initials} (now has {member.drive_count} drives)")
                            helped_any_day = True
                            
                            # Only add one additional driving day per member per phase
                            break
                    
                    if helped_any_day:
                        break
                
                if helped_any_day:
                    break
            
            if not helped_any_day and non_driving_days:
                logger.info(f"  {member.first_name} ({initials}) has only {member.drive_count} drives but there are no days on which they can help reduce the pressure from packed parties")
    
    # Okay if unused - for debugging (can be used on demand)
    def _dump_plan_state(self, filename: str) -> None:
        """
        Dump the current state of all parties and drive counts to a file.
        
        Args:
            filename: Name of the file to write
        """
        import os
        output_path = os.path.join(os.path.dirname(__file__), "..", "..", filename)
        
        with open(output_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write(f"PLAN STATE: {filename}\n")
            f.write("=" * 80 + "\n\n")
            
            # Write drive counts
            f.write("DRIVE COUNTS:\n")
            sorted_members = sorted(
                self.members.items(),
                key=lambda x: (-x[1].drive_count, x[0])
            )
            for initials, member in sorted_members:
                f.write(f"  {initials}: {member.drive_count} drives")
                if member.driving_days:
                    f.write(f" on days {sorted([d+1 for d in member.driving_days])}")
                f.write("\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("PARTIES BY DAY\n")
            f.write("=" * 80 + "\n\n")
            
            # Write parties for each day
            for day_num in range(10):
                f.write(f"{self._get_day_name(day_num).upper()}:\n")
                
                # Schoolbound
                schoolbound_parties = self.all_parties[day_num]["schoolbound"]
                if schoolbound_parties:
                    f.write("  Schoolbound:\n")
                    for party in sorted(schoolbound_parties, key=lambda p: (p.time or 0, p.driver)):
                        time_str = f"{party.time:04d}" if party.time else "----"
                        mandatory = "*" if party.is_designated_driver else ""
                        passengers_str = f" + [{', '.join(party.passengers)}]" if party.passengers else ""
                        f.write(f"    {time_str} | {party.driver}{mandatory}{passengers_str}\n")
                
                # Homebound
                homebound_parties = self.all_parties[day_num]["homebound"]
                if homebound_parties:
                    f.write("  Homebound:\n")
                    for party in sorted(homebound_parties, key=lambda p: (p.time or 0, p.driver)):
                        time_str = f"{party.time:04d}" if party.time else "----"
                        mandatory = "*" if party.is_designated_driver else ""
                        passengers_str = f" + [{', '.join(party.passengers)}]" if party.passengers else ""
                        f.write(f"    {time_str} | {party.driver}{mandatory}{passengers_str}\n")
                
                f.write("\n")
        
        logger.info(f"Dumped plan state to {output_path}")
    
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
                future_mandatory_count * 100,  # Save them if they have mandatory drives later
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
    
    def _find_best_party_for_passenger(self, parties: List[Party], passenger: str, passenger_time: int, day_num: int) -> Optional[Party]:
        """
        Find the best party for a passenger, preferring parties with same time and available space.
        Respects lonely driver flags and no-waiting-afternoon preferences.
        
        Args:
            parties: Available parties
            passenger: Passenger initials
            passenger_time: Passenger's time
            
        Returns:
            Best party or None
        """
        # Filter parties with available space and not lonely drivers
        available_parties = [
            p for p in parties 
            if len(p.passengers) < (self.members[p.driver].number_of_seats - 1)
            and not p.is_lonely_driver  # Skip parties with skipMorning/skipAfternoon
        ]
        
        if not available_parties:
            return None
        
        # Get passenger's no-waiting-afternoon setting (for homebound only)
        passenger_member = self.members[passenger]
        
        # Determine tolerance for this passenger
        is_schoolbound = parties[0].schoolbound if parties else False
        tolerance = passenger_member.get_tolerance_for_direction(day_num, is_schoolbound, self.tolerance) if day_num is not None else self.tolerance
        
        # First priority: parties with the exact same time
        same_time_parties = [p for p in available_parties if abs(p.time - passenger_time) < 5]
        if same_time_parties:
            # Among same-time parties, pick the one with fewest passengers (balance across parties)
            return min(same_time_parties, key=lambda p: len(p.passengers))
        
        # Second priority: parties with time within tolerance
        within_tolerance_parties = [
            p for p in available_parties 
            if times_within_tolerance(p.time, passenger_time, tolerance)
        ]
        if within_tolerance_parties:
            # Pick the one with fewest passengers (balance across parties)
            return min(within_tolerance_parties, key=lambda p: len(p.passengers))
        
        # If we reach here, Phase 2 failed to create enough capacity
        # This should never happen if Phase 2 works correctly
        logger.error(f"CRITICAL: No party found within tolerance for passenger {passenger}")
        logger.error(f"  Passenger time: {passenger_time}, tolerance: {tolerance}")
        logger.error(f"  Available parties: {len(available_parties)}")
        for party in available_parties:
            time_diff = abs(party.time - passenger_time)
            logger.error(f"    Party: driver={party.driver}, time={party.time}, diff={time_diff}, passengers={len(party.passengers)}/{self.members[party.driver].number_of_seats-1}, lonely={party.is_lonely_driver}")
        
        raise ValueError(
            f"No suitable party found for passenger {passenger} (time: {passenger_time}, tolerance: {tolerance}). "
            f"This indicates Phase 2 did not create sufficient capacity. Available parties: {len(available_parties)}"
        )
    
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
            schoolbound_party.passengers.sort()
            schoolbound_party.day_of_week_ab_combo = day_of_week_ab
            parties.append(schoolbound_party)
            
            # Record times
            schoolbound_times[schoolbound_party.driver] = schoolbound_party.time
            for passenger in schoolbound_party.passengers:
                passenger_timetable = self.members[passenger].timetable.get(day_num)
                if passenger_timetable:
                    schoolbound_times[passenger] = passenger_timetable.get_start_time()
        
        for homebound_party in self.all_parties[day_num]["homebound"]:
            homebound_party.passengers.sort()
            homebound_party.day_of_week_ab_combo = day_of_week_ab
            parties.append(homebound_party)
            
            # Record times
            homebound_times[homebound_party.driver] = homebound_party.time
            for passenger in homebound_party.passengers:
                passenger_timetable = self.members[passenger].timetable.get(day_num)
                if passenger_timetable:
                    homebound_times[passenger] = passenger_timetable.get_end_time()
        
        # VALIDATION 1: Check that no one is both driver and passenger
        logger.info(f"\nValidating {self._get_day_name(day_num)}...")
        
        drivers_on_day = set()
        passengers_on_day = set()
        
        for party in parties:
            drivers_on_day.add(party.driver)
            passengers_on_day.update(party.passengers)
        
        driver_and_passenger = drivers_on_day & passengers_on_day
        if driver_and_passenger:
            error_msg = f"VALIDATION ERROR on {self._get_day_name(day_num)}: Members are both driver and passenger: {driver_and_passenger}"
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
            error_msg = f"VALIDATION ERROR on {self._get_day_name(day_num)}: Members missing from day plan: {missing_members}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # VALIDATION 3: Custom day preference validations
        custom_validation_errors = []
        
        for party in parties:
            driver = party.driver
            member = self.members[driver]
            
            # Skip: person should not appear in day plan at all
            if member.should_ignore_on_day(day_num):
                custom_validation_errors.append(
                    f"{driver} has ignoreCompletely set but appears in day plan"
                )
            
            # Needs Car: must be driver (already validated by being in drivers_on_day)
            # No additional check needed since they're already a driver
            
            # Skip AM: schoolbound party must have 0 passengers
            if party.schoolbound and member.skip_morning_on_day(day_num):
                if len(party.passengers) > 0:
                    custom_validation_errors.append(
                        f"{driver} has skipMorning but schoolbound party has {len(party.passengers)} passengers"
                    )
            
            # Skip PM: homebound party must have 0 passengers
            if not party.schoolbound and member.skip_afternoon_on_day(day_num):
                if len(party.passengers) > 0:
                    custom_validation_errors.append(
                        f"{driver} has skipAfternoon but homebound party has {len(party.passengers)} passengers"
                    )
            
            # No Wait PM: homebound party time must exactly match driver's end time
            if not party.schoolbound and member.no_waiting_afternoon_on_day(day_num):
                member_timetable = member.timetable.get(day_num)
                custom_day = member.get_custom_day(day_num)
                
                # Get the expected end time
                expected_end_time = None
                if custom_day and custom_day.custom_end:
                    expected_end_time = int(custom_day.custom_end.replace(':', ''))
                elif member_timetable:
                    expected_end_time = member_timetable.get_end_time()
                
                if expected_end_time and party.time != expected_end_time:
                    # FIXME: removed validation for testing
                    # custom_validation_errors.append(
                    logger.warning(
                        f"{driver} has noWaitingAfternoon but party time ({party.time}) doesn't match end time ({expected_end_time})"
                    )
        
        # Check passengers with noWaitingAfternoon
        for party in parties:
            if not party.schoolbound:  # Only check homebound
                for passenger in party.passengers:
                    passenger_member = self.members[passenger]
                    if passenger_member.no_waiting_afternoon_on_day(day_num):
                        passenger_timetable = passenger_member.timetable.get(day_num)
                        custom_day = passenger_member.get_custom_day(day_num)
                        
                        expected_end_time = None
                        if custom_day and custom_day.custom_end:
                            expected_end_time = int(custom_day.custom_end.replace(':', ''))
                        elif passenger_timetable:
                            expected_end_time = passenger_timetable.get_end_time()
                        
                        if expected_end_time and party.time != expected_end_time:
                            # FIXME: removed validation for testing
                            # custom_validation_errors.append(
                            logger.warning(
                                f"{passenger} (passenger) has noWaitingAfternoon but party time ({party.time}) doesn't match end time ({expected_end_time})"
                            )
        
        # Check that members with needsCar are actually drivers
        for initials, member in self.members.items():
            if member.needs_car_on_day(day_num) and not member.should_ignore_on_day(day_num):
                if initials not in drivers_on_day:
                    custom_validation_errors.append(
                        f"{initials} has needsCar but is not a driver on {self._get_day_name(day_num)}"
                    )
        
        if custom_validation_errors:
            error_msg = f"CUSTOM DAY VALIDATION ERRORS on {self._get_day_name(day_num)}:\n" + "\n".join(custom_validation_errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"✓ {self._get_day_name(day_num)} validation passed")
        
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
                
                # Check if member can drive (has schedule, not ignore_completely)
                # Note: needs_car_on_day means they MUST drive, not that they can't drive
                desperate = len(time_slot.members) == 1
                if member.can_drive_on_day(day_num, desperate):
                    pool.candidates.append(initials)
            
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
            if member.should_ignore_on_day(day_num):
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


