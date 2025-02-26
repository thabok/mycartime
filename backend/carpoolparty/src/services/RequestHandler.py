import base64
import json
from typing import List

from carpoolparty.src.objects import CustomDay, Person
from carpoolparty.src.services.Controller import calculate_plan
from carpoolparty.src.utils import Util as util
from carpoolparty.src.utils.Config import get as get_config
from flask import Flask, jsonify, request
from flask_cors import CORS
from webuntis.session import Session

logger = util.configure_logging()

app = Flask(__name__)

class RequestHandler:
    def __init__(self):
        self.app = app
        CORS(self.app)
        self.app.add_url_rule('/calculatePlan', 'calculate_plan', self.calculate_plan_req, methods=['POST'])
        self.app.add_url_rule('/check', 'check_status', self.check_status, methods=['GET'])

    def calculate_plan_req(self):
        data = request.get_json()
        
        # convert persons JSON to list of Person objects
        persons = self._parse_persons(data['persons'])

        # login, query timetable and calculate plan
        with Session(
            server=get_config('untisUrl'),
            username=data['username'],
            password=base64.b64decode(data['hash']).decode('utf-8'),
            school=get_config('schoolName'),
            useragent=get_config('appAccessId')
        ).login() as session:
            try:
                logger.debug(f"Successfully logged in as {data['username']}")
                result = calculate_plan(session, persons, data['scheduleReferenceStartDate'])
            except Exception as e:
                logger.error(f"Error while calculating plan: {e}")
                return jsonify({'error': str(e)})
        
        # return result
        logger.debug(f"Returning driving plan to client.")
        util.dump_json(result, 'driving_plan.json', default=lambda o: o.to_dict(), sort_keys=False)
        return json.dumps(result, indent=2, default=lambda o: o.to_dict())

    def check_status(self):
        logger.debug("Received status check request.")
        return jsonify(True)

    def run(self):
        self.app.run(port=1338)
    
    def _parse_persons(self, persons_json:dict) -> List[Person]:
        """
        Parses a JSON dictionary of persons and converts it into a list of Person objects.
        Args:
            persons_json (dict): A dictionary where each key is a person's identifier and the value is another dictionary
                                    containing the person's details and custom day properties.
        Returns:
            List[Person]: A list of Person objects created from the provided JSON dictionary.
        Raises:
            KeyError: If any of the expected keys are missing in the person or custom day JSON dictionaries.
        """
        persons = []
        for person_json in persons_json:
            # map custom day properties
            custom_days = {}
            for custom_day_index, custom_day_json in person_json['customDays'].items():
                day_index = util.to_day_index(custom_day_index)
                custom_start_int = util.time_string_to_int(custom_day_json.get('customStart'))
                custom_end_int = util.time_string_to_int(custom_day_json.get('customEnd'))
                custom_days[day_index] = CustomDay(
                    ignore_completely=custom_day_json.get('ignoreCompletely', False),
                    no_waiting_afternoon=custom_day_json.get('noWaitingAfternoon', False),
                    needs_car=custom_day_json.get('needsCar', False),
                    skip_morning=custom_day_json.get('skipMorning', False),
                    skip_afternoon=custom_day_json.get('skipAfternoon', False),
                    driving_skip=custom_day_json.get('drivingSkip', False),
                    custom_start=custom_start_int,
                    custom_end=custom_end_int
                )
            # map person properties
            persons.append(Person(
                first_name=person_json['firstName'],
                last_name=person_json['lastName'],
                initials=person_json.get('initials', None),
                is_part_time=person_json.get('isPartTime', False),
                number_of_seats=person_json.get('numberOfSeats', 5),
                custom_days=custom_days
            ))
        # return converted list of persons
        logger.debug(f"Received {len(persons)} persons from client: {', '.join([p.first_name for p in persons])}")
        return persons


if __name__ == "__main__":
    RequestHandler().run()
