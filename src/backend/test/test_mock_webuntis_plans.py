"""
End-to-end property tests: the 30 Hogwarts members (mock_data/hogwarts-members.json)
get freshly fabricated timetables from the mock WebUntis server (see
mock_webuntis.py), go through the real TimetableService and SolverService,
and the resulting plan is checked against rules that must hold for *every*
generated plan - in both alternating-weeks and single-week mode.

The mock fabricates new schedules on every query, so each run checks a
different random school. The run's seed is part of every failure message;
re-run a failing case with MOCK_WEBUNTIS_SEED=<seed>.

The solver is cut off after a few seconds without improvement (see AGENTS.md),
so the plan isn't necessarily optimal. The optimization checks below therefore
only flag *locally* avoidable problems - a single drive that could be dropped
with everyone still fitting into the remaining cars - which any incumbent the
solver settles on long enough to hit the cutoff has already eliminated, since
those objective tiers dominate everything else.
"""
import json
import os
import random
import sys
import types
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List

import pytest

backend_src = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(backend_src))

import config  # noqa: E402
import mock_webuntis  # noqa: E402
from models import DrivingPlan, Member, Party  # type: ignore # noqa: E402
from party_eligibility import capacity, desired_time, is_eligible  # type: ignore # noqa: E402
from plan_quality import _can_absorb_all  # type: ignore # noqa: E402
from solver_service import SolverService  # type: ignore # noqa: E402
from timetable_service import TimetableService  # type: ignore # noqa: E402
from utils import WEEKDAY_NAMES, cycle_days, hhmm_to_minutes  # type: ignore # noqa: E402

MOCK_SERVER = 'https://hogwarts.webuntis.com'
MEMBERS_FILE = backend_src / 'mock_data' / 'hogwarts-members.json'
SEED = int(os.environ.get('MOCK_WEBUNTIS_SEED', random.randrange(2 ** 32)))
DIRECTIONS = ('schoolbound', 'homebound')

SOLVE_NO_IMPROVEMENT_SECONDS = 5
SOLVE_MAX_SECONDS = 60


@dataclass
class GeneratedPlan:
    alternating_weeks: bool
    members: Dict[str, Member]
    plan: DrivingPlan
    tolerance: int

    @property
    def label(self) -> str:
        mode = 'alternating' if self.alternating_weeks else 'single-week'
        return f"[MOCK_WEBUNTIS_SEED={SEED}, {mode}]"

    @property
    def days(self) -> range:
        return range(cycle_days(self.alternating_weeks))

    def parties(self, day_num: int, direction: str) -> List[Party]:
        schoolbound = direction == 'schoolbound'
        return [p for p in self.plan.day_plans[day_num + 1].parties if p.schoolbound == schoolbound]

    def is_present(self, shorthand: str, day_num: int, schoolbound: bool) -> bool:
        """Same presence rule as SolverService._collect_presence."""
        member = self.members[shorthand]
        return not member.should_ignore_on_day(day_num) and \
            desired_time(member, day_num, schoolbound) is not None

    def distance(self, passenger: str, party: Party, day_num: int, schoolbound: bool) -> int:
        """Real minutes between a passenger's own time and the party's driver time."""
        own = desired_time(self.members[passenger], day_num, schoolbound)
        return abs(hhmm_to_minutes(own) - hhmm_to_minutes(party.original_driver_time))

    def unified_ab(self, passenger: str, party: Party, day_num: int, direction: str) -> bool:
        """Whether the passenger rides with the same driver on this weekday in
        the other week - placements the week A/B pass may deliberately keep
        even where another party would be closer or less loaded."""
        if not self.alternating_weeks:
            return False
        paired_day = day_num + 5 if day_num < 5 else day_num - 5
        return any(passenger in p.passengers and p.driver == party.driver
                   for p in self.parties(paired_day, direction))

    def driving_days(self, shorthand: str) -> List[int]:
        return [d for d in self.days
                if any(p.driver == shorthand for direction in DIRECTIONS for p in self.parties(d, direction))]

    def available_days(self, shorthand: str) -> List[int]:
        return [d for d in self.days if any(self.is_present(shorthand, d, sb) for sb in (True, False))]

    def could_stop_driving(self, shorthand: str, day_num: int) -> bool:
        """
        Whether `shorthand` could hand in their car on `day_num` - ride along as
        a passenger on every leg instead, with their own passengers
        redistributed too - using only the other parties that already exist,
        without breaking capacity or eligibility.

        Deliberately conservative: legs involving a no-wait-afternoon member
        count as "can't tell", since _can_absorb_all doesn't model that rule's
        three-way (co-passenger) part.
        """
        member = self.members[shorthand]
        if member.needs_car_on_day(day_num):
            return False
        for direction in DIRECTIONS:
            schoolbound = direction == 'schoolbound'
            parties = self.parties(day_num, direction)
            own = next((p for p in parties if p.driver == shorthand), None)
            if own is None:
                continue
            travelling = [x for p in parties for x in [p.driver, *p.passengers]]
            if not schoolbound and any(self.members[x].no_waiting_afternoon_on_day(day_num) for x in travelling):
                return False
            others = [p for p in parties if p is not own]
            if not _can_absorb_all([shorthand, *own.passengers], others, self.members, day_num,
                                   schoolbound, self.tolerance):
                return False
        return True


def _reference_monday() -> datetime:
    """First Monday of September in the mock's current school year."""
    today = date.today()
    start_year = today.year if today.month >= 8 else today.year - 1
    first = date(start_year, 9, 1)
    monday = first + timedelta(days=(7 - first.weekday()) % 7)
    return datetime(monday.year, monday.month, monday.day)


def _expected_default_target(member: Member, alternating_weeks: bool) -> int:
    if not alternating_weeks:
        return config.DEFAULT_TARGET_DRIVE_COUNT_NON_ALTERNATING
    if member.is_part_time:
        return config.DEFAULT_TARGET_DRIVE_COUNT_PARTTIME
    return config.DEFAULT_TARGET_DRIVE_COUNT_FULLTIME


@pytest.fixture(scope='module', params=[True, False], ids=['alternating', 'single-week'])
def generated(request) -> GeneratedPlan:
    alternating_weeks = request.param
    schedule_seeds = random.Random(SEED)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(config, 'ALTERNATING_WEEKS', alternating_weeks)
        # The mock builds a fresh, unseeded random.Random() per query; seeding
        # each one from SEED makes a failing school reproducible.
        mp.setattr(mock_webuntis, 'random',
                   types.SimpleNamespace(Random=lambda: random.Random(schedule_seeds.random())))

        members = [Member.from_dict(person) for person in json.loads(MEMBERS_FILE.read_text())]
        service = TimetableService(server=MOCK_SERVER, use_cache=False)
        service.connect('')
        service.get_timetables_for_members(members, _reference_monday())

        solver = SolverService(
            alternating_weeks=alternating_weeks,
            max_time_in_seconds=SOLVE_MAX_SECONDS,
            stop_after_no_improvement_seconds=SOLVE_NO_IMPROVEMENT_SECONDS,
        )
        plan = solver.calculate_driving_plan(members)

    return GeneratedPlan(alternating_weeks, {m.shorthand: m for m in members}, plan, solver.tolerance)


def test_plan_covers_exactly_the_cycle(generated):
    plan = generated.plan
    assert sorted(plan.day_plans) == [d + 1 for d in generated.days], generated.label
    assert plan.alternating_weeks is generated.alternating_weeks, generated.label
    for day_num in generated.days:
        combo = plan.day_plans[day_num + 1].day_of_week_ab_combo
        assert combo.day_of_week == WEEKDAY_NAMES[day_num % 5], generated.label
        assert combo.is_week_a == (day_num < 5), generated.label

    ab_metrics = {'abDriverMismatch', 'passengerAbStability'}
    if generated.alternating_weeks:
        assert ab_metrics <= set(plan.quality_metrics), generated.label
    else:
        assert not ab_metrics & set(plan.quality_metrics), generated.label


def test_every_present_member_travels_exactly_once_per_leg(generated):
    for day_num in generated.days:
        for direction in DIRECTIONS:
            schoolbound = direction == 'schoolbound'
            travelling = [x for p in generated.parties(day_num, direction) for x in [p.driver, *p.passengers]]
            expected = sorted(i for i in generated.members if generated.is_present(i, day_num, schoolbound))
            assert sorted(travelling) == expected, \
                f"{generated.label} day {day_num} {direction}: travelling {sorted(travelling)}, present {expected}"


def test_drivers_drive_both_ways_and_never_ride_along_the_same_day(generated):
    for day_num in generated.days:
        drivers = {direction: {p.driver for p in generated.parties(day_num, direction)} for direction in DIRECTIONS}
        passengers = {x for direction in DIRECTIONS for p in generated.parties(day_num, direction) for x in p.passengers}
        assert not (drivers['schoolbound'] | drivers['homebound']) & passengers, \
            f"{generated.label} day {day_num}: driver and passenger on the same day"
        for shorthand in drivers['schoolbound'] ^ drivers['homebound']:
            present_both = all(generated.is_present(shorthand, day_num, sb) for sb in (True, False))
            assert not present_both, \
                f"{generated.label} day {day_num}: {shorthand} drives only one way but travels both ways"


def test_parties_respect_capacity_and_solo_preferences(generated):
    for day_num in generated.days:
        for direction in DIRECTIONS:
            schoolbound = direction == 'schoolbound'
            for party in generated.parties(day_num, direction):
                seats = capacity(generated.members[party.driver], day_num, schoolbound)
                assert len(party.passengers) <= seats, \
                    f"{generated.label} day {day_num} {direction}: {party.driver} carries " \
                    f"{len(party.passengers)} with {seats} free seats"
                assert len(set(party.passengers)) == len(party.passengers), generated.label


def test_members_who_need_their_car_always_drive(generated):
    for day_num in generated.days:
        for direction in DIRECTIONS:
            schoolbound = direction == 'schoolbound'
            drivers = {p.driver for p in generated.parties(day_num, direction)}
            for shorthand, member in generated.members.items():
                if member.needs_car_on_day(day_num) and generated.is_present(shorthand, day_num, schoolbound):
                    assert shorthand in drivers, \
                        f"{generated.label} day {day_num} {direction}: {shorthand} needs their car but rides along"


def test_passengers_are_eligible_for_their_party(generated):
    for day_num in generated.days:
        for direction in DIRECTIONS:
            schoolbound = direction == 'schoolbound'
            for party in generated.parties(day_num, direction):
                for passenger in party.passengers:
                    assert is_eligible(passenger, party, generated.members, day_num, schoolbound,
                                       generated.tolerance), \
                        f"{generated.label} day {day_num} {direction}: {passenger} can't ride with {party.driver}"
                    # The co-passenger half of the no-wait rule: nobody in the
                    # car may make a no-wait passenger wait for them.
                    if not schoolbound and generated.members[passenger].no_waiting_afternoon_on_day(day_num):
                        own_time = desired_time(generated.members[passenger], day_num, False)
                        later = [x for x in party.passengers
                                 if desired_time(generated.members[x], day_num, False) > own_time]
                        assert not later, \
                            f"{generated.label} day {day_num}: no-wait passenger {passenger} waits for {later}"


def test_party_time_is_the_earliest_start_or_latest_end_of_its_members(generated):
    for day_num in generated.days:
        for direction in DIRECTIONS:
            schoolbound = direction == 'schoolbound'
            for party in generated.parties(day_num, direction):
                times = [party.original_driver_time] + [
                    desired_time(generated.members[p], day_num, schoolbound) for p in party.passengers
                ]
                assert party.time == (min(times) if schoolbound else max(times)), \
                    f"{generated.label} day {day_num} {direction}: {party.driver}'s party time {party.time}"


def test_drive_counts_match_the_plan(generated):
    for shorthand, member in generated.members.items():
        assert member.drive_count == len(generated.driving_days(shorthand)), f"{generated.label} {shorthand}"
        assert f"({shorthand}): {member.drive_count}" in generated.plan.summary, f"{generated.label} {shorthand}"


def test_every_member_drives_at_least_their_target_where_possible(generated):
    for shorthand, member in generated.members.items():
        assert member.max_drives == _expected_default_target(member, generated.alternating_weeks), \
            f"{generated.label} {shorthand}: target {member.max_drives}"
        floor = min(member.max_drives, len(generated.available_days(shorthand)))
        assert member.drive_count >= floor, \
            f"{generated.label} {shorthand} drives {member.drive_count} times, below {floor}"


def test_nobody_drives_more_than_their_target_unless_required(generated):
    for shorthand, member in generated.members.items():
        if member.drive_count <= member.max_drives:
            continue
        avoidable = [d for d in generated.driving_days(shorthand) if generated.could_stop_driving(shorthand, d)]
        assert not avoidable, \
            f"{generated.label} {shorthand} drives {member.drive_count} times (target {member.max_drives}), " \
            f"but everyone would still fit into the other cars on day(s) {avoidable}"


def test_no_car_preference_is_only_overridden_when_required(generated):
    for shorthand, member in generated.members.items():
        floor = min(member.max_drives, len(generated.available_days(shorthand)))
        for day_num in generated.driving_days(shorthand):
            custom = member.get_custom_day(day_num)
            if not (custom and custom.driving_skip):
                continue
            if member.drive_count - 1 < floor:
                continue  # dropping this drive would break their target instead
            assert not generated.could_stop_driving(shorthand, day_num), \
                f"{generated.label} {shorthand} drives on no-car day {day_num} although " \
                f"everyone would still fit into the other cars"


def test_passengers_ride_with_the_closest_party_that_has_room(generated):
    for day_num in generated.days:
        for direction in DIRECTIONS:
            schoolbound = direction == 'schoolbound'
            parties = generated.parties(day_num, direction)
            for current in parties:
                for passenger in current.passengers:
                    if generated.unified_ab(passenger, current, day_num, direction):
                        continue
                    own_distance = generated.distance(passenger, current, day_num, schoolbound)
                    closer = [
                        p.driver for p in parties
                        if p is not current
                        and len(p.passengers) < capacity(generated.members[p.driver], day_num, schoolbound)
                        and is_eligible(passenger, p, generated.members, day_num, schoolbound, generated.tolerance)
                        and generated.distance(passenger, p, day_num, schoolbound) < own_distance
                    ]
                    assert not closer, \
                        f"{generated.label} day {day_num} {direction}: {passenger} rides with {current.driver} " \
                        f"({own_distance} min off) although {closer} is closer and has room"


def test_passengers_are_spread_evenly_across_equally_close_parties(generated):
    for day_num in generated.days:
        for direction in DIRECTIONS:
            schoolbound = direction == 'schoolbound'
            parties = generated.parties(day_num, direction)
            for heavy in parties:
                for light in parties:
                    if len(heavy.passengers) - len(light.passengers) < 2:
                        continue
                    if len(light.passengers) >= capacity(generated.members[light.driver], day_num, schoolbound):
                        continue
                    movable = [
                        p for p in heavy.passengers
                        if not generated.unified_ab(p, heavy, day_num, direction)
                        and is_eligible(p, light, generated.members, day_num, schoolbound, generated.tolerance)
                        and generated.distance(p, light, day_num, schoolbound)
                        == generated.distance(p, heavy, day_num, schoolbound)
                    ]
                    assert not movable, \
                        f"{generated.label} day {day_num} {direction}: {heavy.driver} carries " \
                        f"{len(heavy.passengers)}, {light.driver} {len(light.passengers)}, and {movable} " \
                        f"would be just as close to {light.driver}"
