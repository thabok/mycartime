"""
Hidden mock/demo WebUntis backend, for testing and screenshots without a real
school's credentials or student/staff data.

Activated when the configured WebUntis server URL is exactly one of the two
sentinel "Hogwarts" URLs (see MOCK_SERVER_MODES) - checked by
TimetableService.connect()/test_connection() before any real network Session
would be created. From then on this module stands in for webuntis_client.Session
entirely: it implements the same public methods (login, logout, schoolyears,
subjects, rooms, klassen, timetable_extended) and returns raw period dicts in
the exact shape real WebUntis sends, so every downstream consumer (filtering,
summarization, the solver, the UI) runs completely unmodified against it.

- "static" always returns the same one of 30 pre-baked schedules for a given
  member, assigned in the order members are first seen (persisted via the
  TimetableService disk cache), cycling if more than 30 distinct members are
  queried.
- "dynamic" fabricates a brand new schedule on every query.

Both modes follow the same generation rules (see generate_schedule):
  - full-time: 12 double periods (90 min) + 1-2 supervisions/week, 0-3
    periods differing between the A and B week.
  - part-time: 8 double periods (90 min) + 1 supervision/week, 0-2 periods
    differing between the A and B week, spread across only 4 of the 5
    weekdays - the fifth (same weekday in week A and B) is left completely
    free of lessons and supervision.

Every generated schedule also complies with Hogwarts's dynamic-timetable
policy: no day has a gap bigger than one double period between its lesson
slots (surrounding breaks don't count), no subject repeats on the same day,
and every supervision duty sits directly before or after one of that day's
lessons.

Both modes are aware of the actual member's `is_part_time` flag (passed
through from TimetableService via `timetable_extended`'s `is_part_time`
argument) rather than guessing it: "dynamic" generates a schedule matching
it on every query, "static" picks among the pre-baked schedules tagged with
the matching `isPartTime` flag in hogwarts-schedules.json.
"""
import itertools
import json
import logging
import random
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from paths import resource_path
from webuntis_client import Element, SchoolYear

logger = logging.getLogger(__name__)

# Server URL -> mock mode. Deliberately not documented anywhere user-facing;
# discoverable only by whoever types one of these exact URLs into the Server
# URL field in Settings.
MOCK_SERVER_MODES = {
    'https://hogwarts.webuntis.com/static': 'static',
    'https://hogwarts.webuntis.com/dynamic': 'dynamic',
}

MAX_MOCK_MEMBERS = 30

# A Monday, used purely as an arbitrary but fixed reference point to alternate
# every real-world Monday..Friday between this module's own two internal week
# patterns (see MockSession.timetable_extended for why the choice of anchor
# doesn't matter to the caller).
_ANCHOR_MONDAY = date(2024, 1, 1)

# (start, end) HHMM for the five 90-minute double periods.
DOUBLE_PERIOD_SLOTS = [
    (800, 930),
    (945, 1115),
    (1145, 1315),
    (1400, 1530),
    (1540, 1710),
]

# (start, end) HHMM for the five supervision opportunities: the early-morning
# slot plus the four breaks between the double periods above.
SUPERVISION_SLOTS = [
    (745, 800),
    (930, 945),
    (1115, 1145),
    (1315, 1400),
    (1530, 1540),
]

# subject short name -> (long name, room long name)
SUBJECT_ROOMS = {
    'Pot': ('Potions', 'The Dungeons'),
    'Trf': ('Transfiguration', 'Transfiguration Courtyard'),
    'Chm': ('Charms', 'Charms Classroom'),
    'DADA': ('Defense Against the Dark Arts', 'Defense Classroom'),
    'Hrb': ('Herbology', 'Greenhouse Three'),
    'HoM': ('History of Magic', 'History of Magic Classroom'),
    'Ast': ('Astronomy', 'Astronomy Tower'),
    'Div': ('Divination', 'North Tower'),
    'CoMC': ('Care of Magical Creatures', 'Forbidden Forest Edge'),
    'Arth': ('Arithmancy', 'Arithmancy Classroom'),
    'AnRu': ('Ancient Runes', 'Ancient Runes Tower'),
    'MgSt': ('Muggle Studies', 'Muggle Studies Classroom'),
    'Fly': ('Flying', 'Quidditch Pitch'),
    'Qdd': ('Quidditch Practice', 'Quidditch Pitch'),
    'Alch': ('Alchemy', 'Alchemy Chamber'),
}
SUBJECT_SHORTS = list(SUBJECT_ROOMS.keys())

# supervision short name -> (long name, room long name)
SUPERVISION_DUTIES = {
    'GHD': ('Great Hall Duty', 'Great Hall'),
    'CorP': ('Corridor Patrol', 'Moving Staircases Corridor'),
    'OwlW': ('Owlery Watch', 'Owlery'),
    'CtyW': ('Courtyard Watch', 'Bell Tower Courtyard'),
    'LibD': ('Library Silence Duty', 'Library Restricted Section'),
    'EnHW': ('Entrance Hall Watch', 'Entrance Hall'),
    'PrfB': ('Prefects\' Bathroom Watch', "Prefects' Bathroom"),
}
SUPERVISION_SHORTS = list(SUPERVISION_DUTIES.keys())

# For a given number of occupied double-period slots (0..5 out of the 5 in
# DOUBLE_PERIOD_SLOTS), every subset of that size that doesn't leave 2 or
# more consecutive empty slots between its first and last occupied slot -
# i.e. a schedule gap of more than one double period. Precomputed once since
# the domain is tiny (5 slots -> 32 subsets total).
_VALID_DAY_SLOT_PATTERNS: Dict[int, List[Tuple[int, ...]]] = {
    k: [
        combo for combo in itertools.combinations(range(len(DOUBLE_PERIOD_SLOTS)), k)
        if all(b - a <= 2 for a, b in zip(combo, combo[1:]))
    ]
    for k in range(len(DOUBLE_PERIOD_SLOTS) + 1)
}


def detect_mode(server: Optional[str]) -> Optional[str]:
    """
    Whether the given WebUntis server URL is one of the hidden mock/demo
    sentinel URLs, and if so which mode ('static' or 'dynamic').
    """
    if not server:
        return None
    normalized = server.strip().rstrip('/').lower()
    return MOCK_SERVER_MODES.get(normalized)


def _day_lesson_counts(rng: random.Random, usable_days: List[int], lesson_count: int, day_cap: int) -> Dict[int, int]:
    """
    Split lesson_count across usable_days, each day getting at least 1 (so
    the only lessons-free day is an intended part-time free_day, never an
    incidental one) and at most day_cap.
    """
    counts = {d: 1 for d in usable_days}
    remaining = lesson_count - len(usable_days)
    while remaining > 0:
        candidates = [d for d in usable_days if counts[d] < day_cap]
        if not candidates:
            break
        day = rng.choice(candidates)
        counts[day] += 1
        remaining -= 1
    return counts


def generate_schedule(rng: random.Random, is_part_time: bool) -> Dict[str, List[dict]]:
    """
    Generate one member's fortnightly schedule, following the rules in this
    module's docstring, and the Hogwarts scheduling policy: no gap bigger
    than one double period between a day's occupied double-period slots, no
    subject repeated on the same day, and every supervision duty directly
    before or after one of that day's lessons.

    Returns:
        Dict mapping day_num (0-9, as a string for JSON-friendliness) to a
        list of period specs: {"start": "HH:MM", "end": "HH:MM", "type":
        "lesson"|"supervision", "short": subject/duty short name}.
    """
    lesson_count = 8 if is_part_time else 12
    supervision_count = 1 if is_part_time else rng.randint(1, 2)
    diff_budget = rng.randint(0, 2) if is_part_time else rng.randint(0, 3)

    # Part-time members have one weekday completely free of periods (both
    # lessons and supervision), same weekday in week A and B, so a carpool
    # plan can actually rely on them never needing a ride that day.
    free_day = rng.randrange(5) if is_part_time else None
    usable_days = [d for d in range(5) if d != free_day]

    day_cap = 4 if free_day is None else len(DOUBLE_PERIOD_SLOTS)
    day_counts = _day_lesson_counts(rng, usable_days, lesson_count, day_cap)

    # Which double-period slots are occupied each day - a gap-compliant
    # pattern (see _VALID_DAY_SLOT_PATTERNS), same for week A and B so a
    # subject swap between weeks never changes *when* the member is at
    # school, only *what* they're taught.
    day_slots: Dict[int, Tuple[int, ...]] = {
        day: rng.choice(_VALID_DAY_SLOT_PATTERNS[count]) for day, count in day_counts.items()
    }

    # Week A: assign a subject to each occupied slot, distinct within a day.
    week_a: Dict[tuple, str] = {}
    for day, slots in day_slots.items():
        subjects = rng.sample(SUBJECT_SHORTS, k=len(slots))
        for slot, subject in zip(slots, subjects):
            week_a[(day, slot)] = subject

    # Week B: copy week A, then mutate the subject on a handful of slots,
    # each replacement still distinct from the rest of that day's subjects.
    week_b = dict(week_a)
    mutate_keys = rng.sample(list(week_b.keys()), k=min(diff_budget, len(week_b)))
    for key in mutate_keys:
        day, _slot = key
        day_subjects = {week_b[k] for k in week_b if k[0] == day and k != key}
        alternatives = [s for s in SUBJECT_SHORTS if s not in day_subjects]
        week_b[key] = rng.choice(alternatives)

    # Supervision duties: only in slots directly adjacent to that day's
    # lessons (supervision slot i sits before double-period slot i, and
    # after double-period slot i - 1), same slots for both weeks (a fixed
    # weekly duty), never on the part-time free day.
    supervision_pool = [
        (day, sup_slot)
        for day, slots in day_slots.items()
        for sup_slot in range(len(SUPERVISION_SLOTS))
        if (sup_slot in slots) or (sup_slot - 1 in slots)
    ]
    supervision_slots = rng.sample(supervision_pool, k=min(supervision_count, len(supervision_pool)))
    supervision_duty = {key: rng.choice(SUPERVISION_SHORTS) for key in supervision_slots}

    days: Dict[str, List[dict]] = {}
    for week in (0, 1):  # 0 = A, 1 = B
        lessons = week_a if week == 0 else week_b
        for day in range(5):
            day_num = day + week * 5
            periods = []
            for slot in range(len(DOUBLE_PERIOD_SLOTS)):
                short = lessons.get((day, slot))
                if short:
                    start, end = DOUBLE_PERIOD_SLOTS[slot]
                    periods.append({
                        'start': f'{start // 100:02d}:{start % 100:02d}',
                        'end': f'{end // 100:02d}:{end % 100:02d}',
                        'type': 'lesson',
                        'short': short,
                    })
            for slot in range(len(SUPERVISION_SLOTS)):
                short = supervision_duty.get((day, slot))
                if short:
                    start, end = SUPERVISION_SLOTS[slot]
                    periods.append({
                        'start': f'{start // 100:02d}:{start % 100:02d}',
                        'end': f'{end // 100:02d}:{end % 100:02d}',
                        'type': 'supervision',
                        'short': short,
                    })
            periods.sort(key=lambda p: p['start'])
            days[str(day_num)] = periods

    return days


def _hhmm_from_str(value: str) -> int:
    hours, minutes = value.split(':')
    return int(hours) * 100 + int(minutes)


class MockSession:
    """
    A webuntis_client.Session look-alike backed by fabricated data instead of
    a real WebUntis server. Implements the same public surface TimetableService
    relies on, so it's a drop-in replacement wherever a real Session would go.
    """

    _static_schedules: Optional[List[dict]] = None
    _member_pool: Optional[List[dict]] = None

    def __init__(self, mode: str, cache=None):
        self.mode = mode
        self.cache = cache

    # -- lifecycle -----------------------------------------------------
    def login(self) -> 'MockSession':
        return self

    def logout(self):
        pass

    # -- lookups ---------------------------------------------------------
    def schoolyears(self) -> List[SchoolYear]:
        # A handful of consecutive fake school years spanning today, so
        # whatever reference date a test picks always falls inside one.
        current_year = date.today().year
        years = []
        for offset in range(-2, 3):
            start_year = current_year + offset
            years.append(SchoolYear(
                id=start_year,
                name=f'{start_year}/{start_year + 1}',
                start=_as_datetime(date(start_year, 8, 1)),
                end=_as_datetime(date(start_year + 1, 7, 31)),
            ))
        return years

    def subjects(self) -> List[Element]:
        return [
            Element(id=1000 + i, name=short, long_name=long)
            for i, (short, (long, _room)) in enumerate(SUBJECT_ROOMS.items())
        ]

    def rooms(self) -> List[Element]:
        rooms = {long_room for _long, long_room in SUBJECT_ROOMS.values()} | \
                {long_room for _long, long_room in SUPERVISION_DUTIES.values()}
        return [Element(id=2000 + i, name=r, long_name=r) for i, r in enumerate(sorted(rooms))]

    def klassen(self) -> List[Element]:
        return []

    # -- timetable ---------------------------------------------------------
    def timetable_extended(self, start: int, end: int, teacher: str, teacher_fields: List[str],
                            is_part_time: bool = False) -> List[dict]:
        schedule_days = self._schedule_for(teacher, is_part_time)
        teacher_id = (abs(hash(teacher)) % 900000) + 100000

        start_date = date(start // 10000, (start // 100) % 100, start % 100)
        end_date = date(end // 10000, (end // 100) % 100, end % 100)

        periods = []
        current = start_date
        while current <= end_date:
            weekday = current.weekday()
            if weekday < 5:
                monday = current - timedelta(days=weekday)
                parity = ((monday - _ANCHOR_MONDAY).days // 7) % 2
                day_num = weekday + parity * 5
                for spec in schedule_days.get(str(day_num), []):
                    periods.append(self._raw_period(current, spec, teacher, teacher_id))
            current += timedelta(days=1)
        return periods

    def _raw_period(self, on_date: date, spec: dict, teacher: str, teacher_id: int) -> dict:
        is_supervision = spec['type'] == 'supervision'
        if is_supervision:
            long_name, room = SUPERVISION_DUTIES[spec['short']]
        else:
            long_name, room = SUBJECT_ROOMS[spec['short']]
        return {
            'date': int(on_date.strftime('%Y%m%d')),
            'startTime': _hhmm_from_str(spec['start']),
            'endTime': _hhmm_from_str(spec['end']),
            'code': '',
            # Break supervision has no subject at all - a WebUntis 'bs'
            # period type, surfaced via 'lstype' and picked up by the
            # frontend to render it in its dedicated (lilac) category,
            # distinct from ordinary lessons - see resolvePeriodDisplay in
            # MemberTimetableView.tsx.
            'su': [] if is_supervision else [
                {'id': hash(spec['short']) % 10000, 'name': spec['short'], 'longname': long_name},
            ],
            'lstype': 'bs' if is_supervision else 'ls',
            'lstext': long_name if is_supervision else '',
            'te': [{'id': teacher_id, 'name': teacher, 'orgname': teacher}],
            'ro': [{'id': hash(room) % 10000, 'name': room, 'longname': room}],
            'kl': [],
        }

    # -- schedule assignment -----------------------------------------------
    def _schedule_for(self, teacher: str, is_part_time: bool) -> Dict[str, List[dict]]:
        if self.mode == 'dynamic':
            rng = random.Random()
            return generate_schedule(rng, is_part_time)
        return self._static_schedule_for(teacher, is_part_time)

    def _static_schedule_for(self, teacher: str, is_part_time: bool) -> Dict[str, List[dict]]:
        schedules = self._load_static_schedules()
        # Only pick among schedules matching the member's actual part-time
        # status, so e.g. a part-time member never gets handed a full-time
        # (12-lesson) pre-baked schedule just because of assignment order.
        matching = [i for i, s in enumerate(schedules) if s.get('isPartTime', False) == is_part_time]
        if not matching:
            matching = list(range(len(schedules)))
        index = self._assigned_index(teacher, len(matching))
        return schedules[matching[index]]['days']

    def _assigned_index(self, teacher: str, schedule_count: int) -> int:
        """
        The index a given member (by whatever initials they're queried under)
        was first assigned, persisted across requests via the disk cache
        (shared with TimetableService) so "the Nth member ever seen" keeps
        getting the same fixed schedule forever, cycling past 30. Callers
        pass the count of the subset of schedules actually eligible for that
        member (e.g. matching part-time status), not the whole pool.
        """
        cache_key = 'mock_webuntis_static_assignments'
        if self.cache is None:
            # No persistence available (e.g. the Settings "Test connection"
            # button uses use_cache=False) - fall back to a stable-enough
            # per-name assignment for that one-off call.
            return abs(hash(teacher)) % schedule_count

        assignments = self.cache.get(cache_key) or {}
        if teacher not in assignments:
            assignments[teacher] = len(assignments) % MAX_MOCK_MEMBERS
            self.cache.set(cache_key, assignments)
        return assignments[teacher] % schedule_count

    @classmethod
    def _load_static_schedules(cls) -> List[dict]:
        if cls._static_schedules is None:
            path = resource_path('mock_data', 'hogwarts-schedules.json')
            with open(path, 'r', encoding='utf-8') as f:
                cls._static_schedules = json.load(f)
        return cls._static_schedules


def _as_datetime(d: date):
    from datetime import datetime
    return datetime(d.year, d.month, d.day)


def load_mock_members() -> List[dict]:
    """The 30 Harry-Potter-themed demo members (Member-schema dicts), for
    anything that wants to offer them as ready-made carpool members (e.g. a
    future "load demo members" UI action)."""
    if MockSession._member_pool is None:
        path = resource_path('mock_data', 'hogwarts-members.json')
        with open(path, 'r', encoding='utf-8') as f:
            MockSession._member_pool = json.load(f)
    return MockSession._member_pool
