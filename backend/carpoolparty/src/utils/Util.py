import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from carpoolparty.src.objects import CustomDay, DayPlan, Party, Person, Pool
from carpoolparty.src.utils.Config import get as get_config

logger = None

ON_CALL_SUBSTITUTION_ID = 255
RELEVANT_DAYS = [ 1,2,3,4,5,8,9,10,11,12 ]

def dump_json(data, file):
    with open(file, 'w') as f:
        json.dump(data, f, indent=2, sort_keys=True)

def calculate_date_number(start_date: int, days_to_add: int) -> int:
    start_date_str = str(start_date)
    start_date_obj = datetime.strptime(start_date_str, '%Y%m%d')
    new_date_obj = start_date_obj + timedelta(days=days_to_add)
    new_date_str = new_date_obj.strftime('%Y%m%d')
    return int(new_date_str)

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

def get_opposite_direction(direction: str) -> str:
    return 'homebound' if direction == 'schoolbound' else 'schoolbound'

def is_period_relevant(period, initials) -> bool:
    if period.get('code', '') == 'irregular': return False
    different_orgid = False
    matching_name = False
    for teacher in period['te']:
        if 'orgname' in teacher:
            if teacher['orgname'] == initials:
                # the period is handled by the specified teacher
                matching_name = True
            else:
                # the period is only handled temporarily by the specified teacher 
                different_orgid = True
        elif 'name' in teacher and teacher['name'] == initials:
            matching_name = True

    is_irrelevant = (different_orgid and not matching_name) or is_on_call_substitution(period)
    return not is_irrelevant

def is_on_call_substitution(period) -> bool:
    for subject in period['su']:
        if subject['id'] == ON_CALL_SUBSTITUTION_ID:
            return True
    return False

def get_candidate_pools_of_size(size, candidate_pools) -> List[Pool]:
    pools_of_size = []
    for pool_group in candidate_pools.values():
        pools = pool_group['schoolbound'] + pool_group['homebound']
        for pool in pools:
            if len(pool.persons) == size:
                pools_of_size.append(pool)
    return pools_of_size

def derive_time(party:Party) -> int:
    if party.direction == 'schoolbound': # -> earliest time counts
        time = party.driver.schedule[party.day_index]['startTime']
        for passenger in party.passengers:
            passenger_time = passenger.schedule[party.day_index]['startTime']
            if passenger_time < time:
                time = passenger_time
    else: # homebound -> latest time counts
        time = party.driver.schedule[party.day_index]['endTime']
        for passenger in party.passengers:
            passenger_time = passenger.schedule[party.day_index]['endTime']
            if passenger_time > time:
                time = passenger_time
    return time

def free_seats_in_existing_parties(day_plan:DayPlan, time:int, direction:str, tolerance:int=0) -> int:
    parties = day_plan.get_schoolbound_parties() if direction == 'schoolbound' else day_plan.get_homebound_parties()
    parties = [ party for party in parties if times_match(derive_time(party), time, tolerance) ]
    free_seats = sum(party.driver.number_of_seats - 1 - len(party.passengers) for party in parties)
    return free_seats

def get_person_with_fewest_drives(driving_plan, persons:List[Person], day_index=None) -> Person:
    def can_drive(person:Person, day_index) -> bool:
        custom_day = person.custom_days.get(day_index, CustomDay())
        return not custom_day.driving_skip and not custom_day.ignore_completely
    possible_drivers = [ person for person in persons if day_index and can_drive(person, day_index) ]
    # calculate drives per person
    drives: Dict[Person, int] = { person: get_number_of_drives(person, driving_plan) for person in possible_drivers }
    # return best candidate
    return min(drives, key=drives.get) # type: ignore
    
def get_number_of_drives(person, driving_plan):
    drives = 0
    for day_plan in driving_plan.values():
        for party in day_plan.get_schoolbound_parties() + day_plan.get_homebound_parties():
            if party.driver == person:
                drives += 1
                break
    return drives

def times_match(time1:int, time2:int, tolerance_minutes:int=0) -> bool:
    return abs(time1 - time2) <= tolerance_minutes

def to_day_index(custom_day_index) -> int:
    cdi = int(custom_day_index)
    if cdi <= 4:
        return cdi + 1
    else:
        return cdi + 3

def time_string_to_int(time:str):
    if not time: return None
    assert ':' in time, f"Unexpected time format: {time}"
    return int(time.replace(':', ''))

def configure_logging():
    global logger
    if logger == None:
        logger = logging.getLogger('carpoolparty')
        logger.setLevel(logging.DEBUG)
        file_handler = logging.FileHandler('carpoolparty.log')
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger

def find_closest_time(time:int, times):
    if not times:
        return None
    else:
        return min(times, key=lambda t: abs(t - time))

def get_closest_match(time:int, parties:List[Party]) -> Party:
    if not parties:
        return None # type: ignore
    else:
        closest_time = None
        for party in parties:
            if party.driver.number_of_seats - 1 - len(party.passengers) > 0:
                party_time = derive_time(party)
                if not closest_time or abs(party_time - time) < abs(closest_time - time):
                    closest_time = party_time
            else: continue
    assert closest_time != None, f"Could not find a party with free seats in {parties}"
    parties_with_closest_time = [ party for party in parties if derive_time(party) == closest_time ]
    # from the 1-n parties with the closest time, return the one with the most free seats
    return max(parties_with_closest_time, key=lambda p: p.driver.number_of_seats - 1 - len(p.passengers))

def create_summary_data(driving_plan, persons:List[Person]):
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

    drive_counts = { p : 0 for p in persons }
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
            drive_counts[driver] += 1

    total_drives = sum(drive_counts.values())

    summary['gt4'] = sum(1 for count in drive_counts.values() if count > 4)
    summary['high'] = max(drive_counts.values())
    summary['avg'] = total_drives / len(drive_counts) # total drives * number of persons
    summary['full'] = (float(full_parties) / float(total_parties)) * 100 if total_parties > 0 else 0.0
    summary['drives'] = drive_counts

    return summary
    