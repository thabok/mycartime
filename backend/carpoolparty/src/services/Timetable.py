from datetime import datetime
import diskcache as dc
from webuntis.session import Session
import carpoolparty.src.utils.Util as util
from carpoolparty.src.objects import CustomDay, Person

logger = util.configure_logging()
cache = dc.Cache('./cache_dir')

def fetch_timetable(session: Session, person: Person, start_date: int):
    end_date = util.calculate_date_number(start_date, 100)
    periods = query_timetable(session, person, start_date, end_date)
    # filter out on call substitutions, or other kinds of irrelevant periods
    relevant_periods = [period for period in periods if util.is_period_relevant(period, person.initials)]
    logger.debug(f"Fetching timetable for {person}: found {len(relevant_periods)} relevant periods (of a total {len(periods)})")
    # for each date, add 1 timetable item with start / end time
    timetable = {}
    for period in relevant_periods:
        period_date_obj = datetime.strptime(str(period['date']), '%Y%m%d').date()
        start_date_obj = datetime.strptime(str(start_date), '%Y%m%d').date()
        day_index = ((period_date_obj - start_date_obj).days % 14) + 1
        # ignore weekends
        if not (day_index in range(1,6) or day_index in range(8,13)):
            continue
        timetable_item = timetable.get(day_index)
        if not timetable_item:
            # create new timetable item for given date
            timetable[day_index] = {
                'startTime': period['startTime'],
                'endTime': period['endTime']
            }
        else:
            # update start / end time
            if period['startTime'] < timetable_item['startTime']:
                timetable_item['startTime'] = period['startTime']
            if period['endTime'] > timetable_item['endTime']:
                timetable_item['endTime'] = period['endTime']

    # apply custom start/end times
    for day_index in util.RELEVANT_DAYS:
        custom_day = person.custom_days.get(day_index, CustomDay())
        # apply custom start time
        if custom_day.custom_start:
            timetable_item = timetable.get(day_index)
            if not timetable_item:
                timetable[day_index] = {
                    'startTime': custom_day.custom_start,
                    'endTime': None
                }
            else:
                timetable_item['startTime'] = custom_day.custom_start
        # apply custom end time
        if custom_day.custom_end:
            timetable_item = timetable.get(day_index)
            if not timetable_item:
                timetable[day_index] = {
                    'startTime': None,
                    'endTime': custom_day.custom_end
                }
            else:
                timetable_item['endTime'] = custom_day.custom_end
        # sanity check
        timetable_item = timetable.get(day_index)
        if timetable_item:
            assert timetable_item['startTime'] is not None, f"[{person}] Start time is not defined for {util.day_name(day_index)}"
            assert timetable_item['endTime'] is not None, f"[{person}] End time is not defined for {util.day_name(day_index)}"
    
    person.set_schedule(timetable)
    return timetable

def query_timetable(session: Session, person: Person, start_date: int, end_date: int) -> list:
    cache_key = f"{person.initials}-{start_date}-{end_date}"
    periods = cache.get(cache_key)
    if periods:
        logger.debug(f"Returning cached timetable for {cache_key}")
    else:
        logger.debug(f"No cache available for {cache_key}: fetching timetable from UNTIS API")
        tte = session.timetable_extended(start=start_date, end=end_date, key_type="name", teacher_fields=["id", "name", "externalkey"], teacher=person.initials)
        periods = tte._data
        cache.set(cache_key, periods)
    return periods # type: ignore
