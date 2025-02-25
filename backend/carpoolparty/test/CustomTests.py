import json

import keyring
from webuntis.session import Session

from carpoolparty.src.objects import CustomDay, Person
from carpoolparty.src.services.Controller import calculate_plan
from carpoolparty.src.utils import Util


def test_scenario_a():
    username = "Kc"
    password = keyring.get_password("carpoolparty", username)

    persons = [
        daniel(), anna(),
        Person('Rabea', 'Wirth', 'Wr'),
        Person('Lina', 'Linster', 'Li'),
        Person('Tim', 'Kiel', 'Ki'),
        Person('Laura', 'Freund', 'Fd')
    ]
    start_date = 20250217

    with Session(
        server='https://cissa.webuntis.com',
        username='Kc',
        password=password,
        school='NG Wilhelmshaven',
        useragent='Python'
    ).login() as session:
        result = calculate_plan(session, persons, start_date)
        Util.dump_json(result, 'scenario_a.json')


def daniel():
    return Person('Daniel', 'Hübner', 'Hn', custom_days={
        1: CustomDay(ignore_completely=True),
        2: CustomDay(needs_car=True),
        3: CustomDay(driving_skip=True, custom_start=810, custom_end=1230),
        5: CustomDay(skip_afternoon=True, custom_start=840)
    })

def anna():
    return Person('Anna', 'Siebolds', 'Si', custom_days={
        3: CustomDay(needs_car=True, custom_start=810, custom_end=1230),
        4: CustomDay(driving_skip=True),
        5: CustomDay(driving_skip=True, custom_start=840)
    })


if __name__ == '__main__':
    test_scenario_a()
