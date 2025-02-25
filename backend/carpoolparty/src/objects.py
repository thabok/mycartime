from typing import List

from carpoolparty.src.utils import Util as util


class CustomDay:
    def __init__(self, ignore_completely=False, no_waiting_afternoon=False, needs_car=False, skip_morning=False, skip_afternoon=False, driving_skip=False, custom_start=None, custom_end=None):
        self.ignore_completely = ignore_completely
        self.no_waiting_afternoon = no_waiting_afternoon
        self.needs_car = needs_car
        self.skip_morning = skip_morning
        self.skip_afternoon = skip_afternoon
        self.driving_skip = driving_skip
        self.custom_start = custom_start
        self.custom_end = custom_end

    def to_dict(self):
        return {
            'ignore_completely': self.ignore_completely,
            'no_waiting_afternoon': self.no_waiting_afternoon,
            'needs_car': self.needs_car,
            'skip_morning': self.skip_morning,
            'skip_afternoon': self.skip_afternoon,
            'driving_skip': self.driving_skip,
            'custom_start': self.custom_start,
            'custom_end': self.custom_end
        }

class Person:
    def __init__(self, first_name: str, last_name: str, initials: str, is_part_time: bool = False, number_of_seats: int = 5, schedule={}, custom_days = None):
        self.first_name = first_name
        self.last_name = last_name
        self.initials = initials
        self.is_part_time = is_part_time
        self.number_of_seats = number_of_seats
        self.schedule = schedule
        self.custom_days = custom_days or {}

    def set_schedule(self, schedule):
        self.schedule = schedule
        return self

    def __str__(self):
        return f"{self.first_name} ({self.initials})"
    
    def __repr__(self) -> str:
        return self.__str__()

    def to_dict(self):
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'initials': self.initials,
            'is_part_time': self.is_part_time,
            'number_of_seats': self.number_of_seats,
            'schedule': self.schedule,
            'custom_days': {k: v.to_dict() for k, v in self.custom_days.items()}
        }

class Party:
    def __init__(self, day_index: int, direction: str, driver: Person, passengers = None):
        self.day_index = day_index
        self.direction = direction
        self.driver = driver
        self.passengers: List[Person] = passengers or []

    def __str__(self) -> str:
        s = f"[{util.derive_time(self)}] [{self.driver}] "
        if self.passengers: s += '['
        s += ", ".join([str(passenger) for passenger in self.passengers])
        if self.passengers: s += ']'
        return s
    
    def __repr__(self) -> str:
        return self.__str__()

    def is_lonely_driver(self) -> bool:
        custom_day = self.driver.custom_days.get(self.day_index, CustomDay())
        lonely_morning = custom_day.skip_morning and self.direction == 'schoolbound'
        lonely_afternoon = custom_day.skip_afternoon and self.direction == 'homebound'
        return lonely_morning or lonely_afternoon

    def to_dict(self):
        return {
            'day_index': self.day_index,
            'direction': self.direction,
            'driver': str(self.driver),
            'passengers': [str(p) for p in self.passengers],
            'time' : util.derive_time(self)
        }

class DayPlan:
    def __init__(self, day_index: int):
        self.day_index = day_index
        self.schoolbound_parties: List[Party] = []
        self.homebound_parties: List[Party] = []

    def get_day_index(self) -> int:
        return self.day_index

    def get_schoolbound_parties(self) -> List[Party]:
        return self.schoolbound_parties

    def get_homebound_parties(self) -> List[Party]:
        return self.homebound_parties

    def add_party(self, party: Party):
        if party.direction == 'schoolbound':
            self.schoolbound_parties.append(party)
        elif party.direction == 'homebound':
            self.homebound_parties.append(party)
        else:
            raise ValueError("Direction must be either 'schoolbound' or 'homebound'")

    def __str__(self) -> str:
        s = f"DayPlan {util.day_name(self.day_index, True)} ({len(self.schoolbound_parties)} / {len(self.homebound_parties)}):\n"
        if self.schoolbound_parties:
            s += "Schoolbound parties:\n"
            for party in self.schoolbound_parties:
                s += f"  {party}\n"
        if self.homebound_parties:
            s += "Homebound parties:\n"
            for party in self.homebound_parties:
                s += f"  {party}\n"
        return s
    
    def __repr__(self) -> str:
        return self.__str__()

    def to_dict(self):
        return {
            'day_index': self.day_index,
            'schoolbound_parties': [party.to_dict() for party in self.schoolbound_parties],
            'homebound_parties': [party.to_dict() for party in self.homebound_parties]
        }
    
    def __json__(self):
        return self.to_dict()

class Pool:
    def __init__(self, day_index:int, direction:str, time:int, persons:List[Person], tolerance_minutes:int):
        self.day_index = day_index
        self.direction = direction
        self.time = time
        self.persons = persons
        self.tolerance_minutes = tolerance_minutes

    def __str__(self):
        return f"{util.day_name(self.day_index)} {self.direction} {self.time} {self.persons} {self.tolerance_minutes if self.tolerance_minutes else ''}"
    
    def __repr__(self):
        return self.__str__()
    
    def to_dict(self):
        return {
            'day_index': self.day_index,
            'direction': self.direction,
            'time': self.time,
            'persons': [str(p) for p in self.persons],
            'tolerance_minutes': self.tolerance_minutes
        }
