"""
Turns already-decided Party objects into validated DayPlan/DrivingPlan output.

This is deliberately engine-agnostic: SolverService (see solver_service.py)
decides *who drives whom*, then hands the resulting parties to PlanBuilder to
construct the TimeInfo-annotated DayPlan objects the frontend expects, and to
run the same VALIDATION 1/2/3 checks regardless of which engine produced the
parties.
"""
import logging
from typing import Dict, List

from models import DayOfWeekABCombo, DayPlan, Member, Party, TimeInfo

logger = logging.getLogger(__name__)


class PlanBuilder:
    """Builds validated DayPlan objects and the plan summary from decided parties."""

    def __init__(self, members: Dict[str, Member], all_parties: Dict[int, Dict[str, List[Party]]]):
        self.members = members
        self.all_parties = all_parties

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

    def build_day_plan(self, day_num: int, day_of_week_ab: DayOfWeekABCombo) -> DayPlan:
        """
        Build a day plan from the parties decided for this day.
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
        schoolbound_time_info = {}
        homebound_time_info = {}

        # Collect all parties for this day
        for schoolbound_party in self.all_parties[day_num]["schoolbound"]:
            schoolbound_party.passengers.sort()
            schoolbound_party.day_of_week_ab_combo = day_of_week_ab
            parties.append(schoolbound_party)

            # Record times for driver
            schoolbound_times[schoolbound_party.driver] = schoolbound_party.time

            # Build TimeInfo for driver (schoolbound direction)
            driver_member = self.members[schoolbound_party.driver]
            driver_custom = driver_member.get_custom_day(day_num)
            driver_timetable = driver_member.timetable.get(day_num)

            timetable_time = None
            custom_pref_time = None

            if driver_timetable:
                timetable_time = driver_timetable.get_scheduled_start_time()
            if driver_custom and driver_custom.custom_start:
                custom_pref_time = int(driver_custom.custom_start.replace(':', ''))

            schoolbound_time_info[schoolbound_party.driver] = TimeInfo(
                timetable_time=timetable_time,
                custom_pref_time=custom_pref_time,
                effective_time=schoolbound_party.time
            )

            # Record times for passengers
            for passenger in schoolbound_party.passengers:
                passenger_timetable = self.members[passenger].timetable.get(day_num)
                if passenger_timetable:
                    passenger_time = passenger_timetable.get_start_time()
                    schoolbound_times[passenger] = passenger_time

                    # Build TimeInfo for passenger (schoolbound direction)
                    passenger_member = self.members[passenger]
                    passenger_custom = passenger_member.get_custom_day(day_num)

                    pass_timetable_time = None
                    pass_custom_pref_time = None

                    if passenger_timetable:
                        pass_timetable_time = passenger_timetable.get_scheduled_start_time()
                    if passenger_custom and passenger_custom.custom_start:
                        pass_custom_pref_time = int(passenger_custom.custom_start.replace(':', ''))

                    schoolbound_time_info[passenger] = TimeInfo(
                        timetable_time=pass_timetable_time,
                        custom_pref_time=pass_custom_pref_time,
                        effective_time=passenger_time
                    )

        for homebound_party in self.all_parties[day_num]["homebound"]:
            homebound_party.passengers.sort()
            homebound_party.day_of_week_ab_combo = day_of_week_ab
            parties.append(homebound_party)

            # Record times for driver
            homebound_times[homebound_party.driver] = homebound_party.time

            # Build TimeInfo for driver (homebound direction)
            driver_member = self.members[homebound_party.driver]
            driver_custom = driver_member.get_custom_day(day_num)
            driver_timetable = driver_member.timetable.get(day_num)

            timetable_time = None
            custom_pref_time = None

            if driver_timetable:
                timetable_time = driver_timetable.get_scheduled_end_time()
            if driver_custom and driver_custom.custom_end:
                custom_pref_time = int(driver_custom.custom_end.replace(':', ''))

            homebound_time_info[homebound_party.driver] = TimeInfo(
                timetable_time=timetable_time,
                custom_pref_time=custom_pref_time,
                effective_time=homebound_party.time
            )

            # Record times for passengers
            for passenger in homebound_party.passengers:
                passenger_timetable = self.members[passenger].timetable.get(day_num)
                if passenger_timetable:
                    passenger_time = passenger_timetable.get_end_time()
                    homebound_times[passenger] = passenger_time

                    # Build TimeInfo for passenger (homebound direction)
                    passenger_member = self.members[passenger]
                    passenger_custom = passenger_member.get_custom_day(day_num)

                    pass_timetable_time = None
                    pass_custom_pref_time = None

                    if passenger_timetable:
                        pass_timetable_time = passenger_timetable.get_scheduled_end_time()
                    if passenger_custom and passenger_custom.custom_end:
                        pass_custom_pref_time = int(passenger_custom.custom_end.replace(':', ''))

                    homebound_time_info[passenger] = TimeInfo(
                        timetable_time=pass_timetable_time,
                        custom_pref_time=pass_custom_pref_time,
                        effective_time=passenger_time
                    )

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

            # Skip AM: schoolbound party must have 0 passengers
            if party.schoolbound and member.solo_am_on_day(day_num):
                if len(party.passengers) > 0:
                    custom_validation_errors.append(
                        f"{driver} has soloAm but schoolbound party has {len(party.passengers)} passengers"
                    )

            # Skip PM: homebound party must have 0 passengers
            if not party.schoolbound and member.solo_pm_on_day(day_num):
                if len(party.passengers) > 0:
                    custom_validation_errors.append(
                        f"{driver} has soloPm but homebound party has {len(party.passengers)} passengers"
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
            homebound_times_by_initials=homebound_times,
            schoolbound_time_info_by_initials=schoolbound_time_info,
            homebound_time_info_by_initials=homebound_time_info
        )

    def generate_summary(self, members: List[Member]) -> str:
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
