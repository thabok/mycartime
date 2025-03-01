import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from carpoolparty.src.objects import (CustomDay, DayPlan, Party, Person, Pool,
                                      day_name)
from carpoolparty.src.utils.Config import get as get_config

logger = None

ON_CALL_SUBSTITUTION_ID = 255
RELEVANT_DAYS = [ 1,2,3,4,5,8,9,10,11,12 ]

def dump_json(data, file, default=None, sort_keys=True):
    with open(file, 'w') as f:
        json.dump(data, f, indent=2, sort_keys=sort_keys, default=default)

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

def get_pools(candidate_pools, day_index=None, direction=None) -> List[Pool]:
    valid_pools = []
    for pool_group in candidate_pools.values():
        # direction
        pools = pool_group[direction] if direction else (pool_group['schoolbound'] + pool_group['homebound'])
        # day_index
        pools = [ pool for pool in pools if not day_index or pool.day_index == day_index ]
        # collect valid pools
        valid_pools += pools
    return valid_pools

def free_seats_in_existing_parties(day_plan:DayPlan, time:int, direction:str, tolerance:int=0) -> int:
    parties = day_plan.get_schoolbound_parties() if direction == 'schoolbound' else day_plan.get_homebound_parties()
    parties = [ party for party in parties if times_match(party.derive_time(), time, tolerance) ]
    free_seats = sum(party.driver.number_of_seats - 1 - len(party.passengers) for party in parties)
    return free_seats

def find_best_driver(driving_plan, pool:Pool, candidate_pools, tolerance) -> Person:
    day_index = pool.day_index
    day_plan = driving_plan[day_index]
    logger = configure_logging()
    
    def wants_to_drive(person:Person, day_index) -> bool:
        custom_day = person.custom_days.get(day_index, CustomDay())
        return not custom_day.driving_skip and not custom_day.ignore_completely
    
    # prevent persons from driving if they are already a driver or passenger in a party on this day
    def can_drive(person:Person, day_index) -> bool:
        parties = driving_plan[day_index].get_schoolbound_parties() + driving_plan[day_index].get_homebound_parties()
        already_driver = any(person == party.driver for party in parties)
        already_passenger = any(person in party.passengers for party in parties)
        return not (already_driver or already_passenger)
    
    candidates = [ person for person in pool.persons if can_drive(person, day_index) ]
    if not candidates:
        raise Exception("Didn't find any candidates to drive." + day_name(day_index) if day_index else '')
    possible_drivers = [ candidate for candidate in candidates if day_index and wants_to_drive(candidate, day_index) ]
    if not possible_drivers:
        logger.warning("  No one can drive if we acknowledge custom day preferences. Will ignore them and consider everyone as a driver candidate.")
        possible_drivers = candidates

    # calculate drives per person
    drives: Dict[Person, int] = { person: get_number_of_drives(person, driving_plan) for person in possible_drivers }
    min_no_drives = min(drives.values())
    persons_with_min_drives = [ person for person in possible_drivers if drives[person] == min_no_drives ]
    if len(persons_with_min_drives) > 1:
        return get_driver_who_closes_gap_in_other_direction(persons_with_min_drives, candidate_pools, pool, day_plan, tolerance, logger)
    else: # only one person with the fewest drives 
        return persons_with_min_drives[0]

    
def get_driver_who_closes_gap_in_other_direction(persons_with_min_drives, candidate_pools, pool, day_plan, tolerance, logger):
    logger.debug(f"  Multiple persons have the same number of drives: {persons_with_min_drives}. Now searching for good pool coverage in other direction.")
    # ideally, we want to have a driver from a pool (other direction) that still needs drivers
    pools_opposite_direction = get_pools(candidate_pools, pool.day_index, get_opposite_direction(pool.direction))
    drivers_of_current_direction = [ p.driver for p in (day_plan.schoolbound_parties if pool.direction == 'schoolbound' else day_plan.homebound_parties) ]
    # iterate over pools in the opposite direction until none are left
    while pools_opposite_direction:
        smallest_pool = min(pools_opposite_direction, key=lambda p: len(p.persons))
        overlapping_driver_candidate = next((d for d in persons_with_min_drives if d in smallest_pool.persons), None)
        pool_already_covered = any(d in smallest_pool.persons for d in drivers_of_current_direction)
        needs_parties = needs_more_parties(smallest_pool, day_plan, tolerance)
        if not pool_already_covered and needs_parties and overlapping_driver_candidate:
            logger.debug(f"  Found a pool with a driver from the current direction: {smallest_pool}")
            return overlapping_driver_candidate
        else:
            pools_opposite_direction.remove(smallest_pool) # move on to the next one
    # if we didn't find a good candidate, we will just pick the first one
    logger.debug("  Couldn't find a good candidate. Will pick the first one.")
    return persons_with_min_drives[0]

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
                party_time = party.derive_time()
                if not closest_time or abs(party_time - time) < abs(closest_time - time):
                    closest_time = party_time
            else: continue
    assert closest_time != None, f"Could not find a party with free seats in {parties}"
    parties_with_closest_time = [ party for party in parties if party.derive_time() == closest_time ]
    # from the 1-n parties with the closest time, return the one with the most free seats
    return max(parties_with_closest_time, key=lambda p: p.driver.number_of_seats - 1 - len(p.passengers))

def needs_more_parties(pool:Pool, day_plan:DayPlan, tolerance:int) -> bool:
    free_seats_in_parties = free_seats_in_existing_parties(day_plan, pool.time, pool.direction, tolerance)
    return free_seats_in_parties < len(pool.persons)
