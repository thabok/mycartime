from typing import List


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
    
    def to_minimal_dict(self):
        return {
            'first_name': self.first_name,
            'initials': self.initials
        }

class Party:
    def __init__(self, day_index: int, direction: str, driver: Person, passengers = None, designated_driver:bool = False):
        self.day_index = day_index
        self.direction = direction
        self.driver = driver
        self.passengers: List[Person] = passengers or []
        self.designated_driver = designated_driver
        self.lonely_driver, self.problem_driver = self.check_driver_prefs()

    def __str__(self) -> str:
        s = f"[{self.derive_time()}] [{self.driver}] "
        if self.passengers: s += '['
        s += ", ".join([str(passenger) for passenger in self.passengers])
        if self.passengers: s += ']'
        return s
    
    def __repr__(self) -> str:
        return self.__str__()

    def derive_time(self) -> int:
        if self.direction == 'schoolbound': # -> earliest time counts
            time = self.driver.schedule[self.day_index]['startTime']
            for passenger in self.passengers:
                passenger_time = passenger.schedule[self.day_index]['startTime']
                if passenger_time < time:
                    time = passenger_time
        else: # homebound -> latest time counts
            time = self.driver.schedule[self.day_index]['endTime']
            for passenger in self.passengers:
                passenger_time = passenger.schedule[self.day_index]['endTime']
                if passenger_time > time:
                    time = passenger_time
        return time

    def check_driver_prefs(self) -> tuple[bool, bool]:
        custom_day = self.driver.custom_days.get(self.day_index, CustomDay())
        lonely_morning = custom_day.skip_morning and self.direction == 'schoolbound'
        lonely_afternoon = custom_day.skip_afternoon and self.direction == 'homebound'
        lonely_driver = (lonely_morning or lonely_afternoon)
        problem_driver = custom_day.driving_skip
        return lonely_driver, problem_driver

    def to_dict(self):
        return {
            'day_index': self.day_index,
            'direction': self.direction,
            'driver': self.driver.to_minimal_dict(),
            'passengers': [p.to_minimal_dict() for p in self.passengers],
            'time' : self.derive_time()
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
        s = f"DayPlan {day_name(self.day_index, True)} ({len(self.schoolbound_parties)} / {len(self.homebound_parties)}):\n"
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
            'schoolbound_parties': [party.to_dict() for party in self.schoolbound_parties].sort(key=lambda p: p['time']),
            'homebound_parties': [party.to_dict() for party in self.homebound_parties].sort(key=lambda p: p['time'])
        }

    

class Pool:
    def __init__(self, day_index:int, direction:str, time:int, persons:List[Person], tolerance_minutes:int):
        self.day_index = day_index
        self.direction = direction
        self.time = time
        self.persons = persons
        self.tolerance_minutes = tolerance_minutes

    def __str__(self):
        return f"{day_name(self.day_index)} {self.direction} {self.time} {self.persons} {self.tolerance_minutes if self.tolerance_minutes else ''}"
    
    def __repr__(self):
        return self.__str__()
    
    def to_dict(self):
        return {
            'day_index': self.day_index,
            'direction': self.direction,
            'time': self.time,
            'persons': [ p.to_minimal_dict() for p in self.persons],
            'tolerance_minutes': self.tolerance_minutes
        }

class ResultWrapper:
    def __init__(self, driving_plan:dict, persons:List[Person]):
        self.plan = driving_plan
        self.persons = persons
        self.summary = create_summary_data(driving_plan, persons)

    def to_dict(self):
        return {
            'plan': self.plan,
            'summary': self.summary,
            'persons': [p.to_dict() for p in self.persons]
        }
    
    def __str__(self):
        s = "\n".join([f"{p}: {n}" for p, n in self.summary['drives'].items()])
        return s
    
    def __repr__(self):
        return self.__str__()

# ---------------------------------------------------
# Helper Functions
# ---------------------------------------------------

def create_summary_data(driving_plan, persons:List[Person]):
    def person_key(person:Person): return f"{person.first_name} ({person.initials})"

    # create summary data for the following criteria:
    # 1. gt4:  how many persons are driving more than 4 times?
    # 2. high: highest number of drives
    # 3. avg:  average number of drives per person
    # 4. full: percentage of parties that are full (driver + number of passengers == driver.number_of_seats)
    summary = {
        'gt4': 0,
        'high': 0,
        'avg': 0.0,
        'full': 0.0,
        'drives': {}
    }

    drive_counts = { person_key(p) : 0 for p in persons }
    total_drives = 0
    total_parties = 0
    full_parties = 0

    for day_plan in driving_plan.values():
        # using a set to prevents duplicates due to schoolbound+homebound
        # can't just take one of the two, because sometimes people are missing in one of the directions
        drivers_of_day = set()
        for party in day_plan.get_schoolbound_parties() + day_plan.get_homebound_parties():
            # count drives
            drivers_of_day.add(party.driver)
            # count full parties
            if len(party.passengers) == party.driver.number_of_seats - 1:
                full_parties += 1
            # count all parties
            total_parties += 1

        # sum up drives for the current day
        for driver in drivers_of_day:
            drive_counts[person_key(driver)] += 1

    total_drives = sum(drive_counts.values())

    summary['gt4'] = sum(1 for count in drive_counts.values() if count > 4)
    summary['high'] = max(drive_counts.values())
    summary['avg'] = total_drives / len(drive_counts) # total drives * number of persons
    summary['full'] = (float(full_parties) / float(total_parties)) * 100 if total_parties > 0 else 0.0
    summary['drives'] = dict(sorted(drive_counts.items()))

    return summary

def day_name(day_index: int, unispaced=False) -> str:
    if day_index == 1:  return f'Monday {" "*(3 if unispaced else 0)}A'
    if day_index == 2:  return f'Tuesday {" "*(2 if unispaced else 0)}A'
    if day_index == 3:  return f'Wednesday A'
    if day_index == 4:  return f'Thursday {" "*(1 if unispaced else 0)}A'
    if day_index == 5:  return f'Friday {" "*(3 if unispaced else 0)}A'
    if day_index == 8:  return f'Monday {" "*(3 if unispaced else 0)}B'
    if day_index == 9:  return f'Tuesday {" "*(2 if unispaced else 0)}B'
    if day_index == 10: return f'Wednesday B'
    if day_index == 11: return f'Thursday {" "*(1 if unispaced else 0)}B'
    if day_index == 12: return f'Friday {" "*(3 if unispaced else 0)}B'
    return 'Unknown'
