import json
from typing import List

from carpoolparty.src.objects import CustomDay, DayPlan, Party, Person, Pool
from carpoolparty.src.services.Timetable import fetch_timetable
from carpoolparty.src.utils import Util as util
from carpoolparty.src.utils.Config import get as get_config
from webuntis.session import Session

logger = util.configure_logging()
TOLERANCE = get_config('acceptableToleranceMinutes')

def calculate_plan(session: Session, persons: list, start_date: int) -> dict[int, DayPlan]:
    logger.info(f"Calculating plan for {len(persons)} persons starting on {start_date}")
    for person in persons: fetch_timetable(session, person, start_date)
    driving_plan = { day_index: DayPlan(day_index) for day_index in util.RELEVANT_DAYS }
    
    # create candidate pools (grouped by start and end time)
    candidate_pools = create_candidate_pools(persons)
    logger.info(f"Driving Plan after 'create_candidate_pools':\n" + "\n".join(str(driving_plan[k]).split('\n')[0] for k in driving_plan.keys()))

    for pool_size in range(1, len(persons)+1):
        pools_of_size_n = util.get_candidate_pools_of_size(pool_size, candidate_pools)
        logger.debug(f"\nConsidering {len(pools_of_size_n)} pools of size {pool_size}:")
        for pool_of_size_n in pools_of_size_n:
            if not pool_of_size_n.persons: continue
            logger.debug(f"\n  Handling {pool_of_size_n}")
            day_plan = driving_plan[pool_of_size_n.day_index]
            
            # 1. while (number of available seats in existing parties is smaller < than the pool size): create new parties
            # -> create party with person with fewest drives and add to driving_plan
            # -> remove person from pool
            create_needed_parties(driving_plan, pool_of_size_n, day_plan, candidate_pools)
            
            # 3. allocate remaining persons in existing parties
            # -> add person to party with the highest number of seats
            # -> remove person from pool
            allocate_remaining_persons(pool_of_size_n, day_plan)

        logger.info(f"Driving Plan at the end of pool_size {pool_size}':\n" + "\n".join(str(driving_plan[k]).split('\n')[0] for k in driving_plan.keys()))
        summary = util.create_summary_data(driving_plan, persons)
        logger.info(summary['drives'])
        for day_plan in driving_plan.values():
            day_plan.schoolbound_parties.sort(key=lambda party: util.derive_time(party))
            day_plan.homebound_parties.sort(key=lambda party: util.derive_time(party))
    
    logger.debug(json.dumps(driving_plan, indent=2, default=lambda o: o.to_dict()))
    summary = util.create_summary_data(driving_plan, persons)

    return driving_plan

def create_needed_parties(driving_plan, pool_of_size_n:Pool, day_plan:DayPlan, candidate_pools):
    logger.debug(f"  Creating needed parties for {pool_of_size_n}")
    day_index = pool_of_size_n.day_index
    free_seats_in_parties = util.free_seats_in_existing_parties(day_plan, pool_of_size_n.time, pool_of_size_n.direction, TOLERANCE)
    logger.debug(f"  Free seats in existing parties: {free_seats_in_parties}")

    while free_seats_in_parties < len(pool_of_size_n.persons):
        person = util.get_person_with_fewest_drives(driving_plan, pool_of_size_n.persons, day_plan.get_day_index())
        logger.debug(f"  Person from this pool with the fewest number of drives: {person}")
        
        # handle this direction
        party = Party(day_index, pool_of_size_n.direction, person)
        logger.debug(f"  {pool_of_size_n.direction.capitalize()}: {party}")
        day_plan.add_party(party)
        pool_of_size_n.persons.remove(person)
        
        # handle other direction
        other_direction = util.get_opposite_direction(pool_of_size_n.direction)
        other_time = person.schedule[day_index]['startTime' if other_direction == 'schoolbound' else 'endTime']
        other_party = Party(day_index, other_direction, person)
        logger.debug(f"  {other_direction.capitalize()}: {other_party}")
        day_plan.add_party(other_party)
        pool = next((pool for pool in candidate_pools[day_index][other_direction] if util.times_match(pool.time, other_time)), None)
        if pool and person in pool.persons:
            logger.debug(f"  Removing {person} from pool {pool}")
            pool.persons.remove(person)
        
        # update free seats number
        free_seats_in_parties = util.free_seats_in_existing_parties(day_plan, pool_of_size_n.time, pool_of_size_n.direction, TOLERANCE)
        logger.debug(f"  Free seats in existing parties: {free_seats_in_parties}, remaining persons in pool: {len(pool_of_size_n.persons)}")

def allocate_remaining_persons(pool_of_size_n:Pool, day_plan:DayPlan):
    if pool_of_size_n.persons: logger.debug(f"  Allocating remaining {len(pool_of_size_n.persons)} persons to existing parties")
    persons_to_remove = []
    for person in pool_of_size_n.persons:
        logger.debug(f"  Allocating {person}...")
        desired_time = person.schedule[pool_of_size_n.day_index].get('startTime' if pool_of_size_n.direction == 'schoolbound' else 'endTime')
        parties_of_same_direction:List[Party] = day_plan.get_schoolbound_parties() if pool_of_size_n.direction == 'schoolbound' else day_plan.get_homebound_parties()
        # try without tolerance (only exact time matches)
        matching_parties:List[Party] = [ party for party in parties_of_same_direction if util.times_match(util.derive_time(party), desired_time) ]
        if matching_parties:
            logger.debug(f"  Found {len(matching_parties)} matching parties (exact time match)")
            # best party is the one with most free seats
            best_party = max(matching_parties, key=lambda p: (p.driver.number_of_seats - 1 - len(p.passengers)))
            logger.debug(f"  Best party: {best_party} (most free seats)")
        else:
            # try with tolerance
            logger.debug(f"  No matching parties with zero tolerance -> applying tolerance of {TOLERANCE} minutes")
            matching_parties = [ party for party in parties_of_same_direction if util.times_match(util.derive_time(party), desired_time, TOLERANCE) ]
            best_party = util.get_closest_match(desired_time, matching_parties)
            logger.debug(f"  Best party: {best_party} (1. closest time, 2. most free seats)")
        
        logger.debug(f"  Adding {person} to {best_party}")
        best_party.passengers.append(person)
        # to prevent concurrent modification -> collect persons to remove
        persons_to_remove.append(person)

    if persons_to_remove: logger.debug(f"  Removing {persons_to_remove} from the pool (they've been allocated in existing parties)")
    # removing allocated persons from the pool
    for person in persons_to_remove:
        pool_of_size_n.persons.remove(person)


def create_candidate_pools(persons: List[Person]):
    candidate_pools = { day_index: { 'schoolbound' : [], 'homebound' : [] } for day_index in util.RELEVANT_DAYS }
    for day_index in util.RELEVANT_DAYS:
        candidate_pools[day_index]['schoolbound'] = create_pools(day_index, persons, 'startTime', TOLERANCE)
        candidate_pools[day_index]['homebound'] = create_pools(day_index, persons, 'endTime', TOLERANCE)
    return candidate_pools


def create_pools(day_index, persons, start_or_end_time, tolerance_minutes=0) -> list[Pool]:
    persons_by_time = {}
    for person in persons:
        # Skip persons based on custom preferences
        custom_pref = person.custom_days.get(day_index, CustomDay())
        if      custom_pref.ignore_completely \
            or (custom_pref.skip_afternoon and start_or_end_time == 'endTime') \
            or (custom_pref.skip_morning and start_or_end_time == 'startTime'):
            continue
        timetable_item = person.schedule.get(day_index)
        if timetable_item: # person has timetable for this day
            time = timetable_item[start_or_end_time]
            
            # get group of persons with the same time (is it exists)
            group = persons_by_time.get(time)
            if not group: # check if there is a time close enough to this one
                closest_time = util.find_closest_time(time, persons_by_time.keys())
                if closest_time and abs(time - closest_time) <= tolerance_minutes:
                    group = persons_by_time[closest_time]
                else:
                    persons_by_time[time] = []
                    group = persons_by_time[time]

            # add person to the group with exact or closest time
            group.append(person)

    # create pools of people driving at the same time
    pools = []
    for time, persons in persons_by_time.items():
        direction = 'schoolbound' if start_or_end_time == 'startTime' else 'homebound'
        pools.append(Pool(
            day_index=day_index,
            direction=direction,
            time=time,
            persons=persons,
            tolerance_minutes=tolerance_minutes))
    return pools


def print_persons_by_time(day_name, persons_by_start_time, persons_by_end_time):
    print(f"Day {day_name}:")
    print(" Schoolbound")
    for start_time, candidates in persons_by_start_time.items():
        print(f"  {start_time}: {', '.join([str(c) for c in candidates])}")
    print(" Homebound")
    for end_time, candidates in persons_by_end_time.items():
        print(f"  {end_time}: {', '.join([str(c) for c in candidates])}")

