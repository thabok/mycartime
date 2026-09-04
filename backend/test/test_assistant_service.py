"""
Unit tests for assistant_service: response envelope parsing and
movePassenger action validation. Pure unit tests, no network/CLI calls.
"""
import sys
from pathlib import Path

backend_src = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(backend_src))

from assistant_service import _parse_envelope, _validate_actions, _validate_move_passenger  # type: ignore
from assistant_service import _drop_capacity_violating_move_passengers  # type: ignore
from assistant_service import _extract_partial_reply  # type: ignore


def test_extract_partial_reply_returns_none_before_value_starts():
    assert _extract_partial_reply('```json\n{"re') is None
    assert _extract_partial_reply('```json\n{"reply":') is None


def test_extract_partial_reply_returns_text_decoded_so_far():
    assert _extract_partial_reply('```json\n{"reply": "Hi the') == 'Hi the'


def test_extract_partial_reply_handles_complete_string():
    buffer = '```json\n{"reply": "Hi there", "actions": []}\n```'
    assert _extract_partial_reply(buffer) == 'Hi there'


def test_extract_partial_reply_decodes_escapes():
    buffer = r'{"reply": "Line1\nLine2 \"quoted\" and é"'
    assert _extract_partial_reply(buffer) == 'Line1\nLine2 "quoted" and é'


def test_extract_partial_reply_stops_before_incomplete_escape():
    # A chunk boundary can split an escape sequence; decode only what's whole.
    assert _extract_partial_reply('{"reply": "Line1\\') == 'Line1'
    assert _extract_partial_reply('{"reply": "abc\\u00e') == 'abc'


def test_parse_envelope_extracts_fenced_json():
    text = 'Sure, here you go:\n```json\n{"reply": "Hi there", "actions": []}\n```\n'
    envelope = _parse_envelope(text)
    assert envelope == {'reply': 'Hi there', 'actions': []}


def test_parse_envelope_extracts_bare_fence():
    text = '```\n{"reply": "Hi", "actions": [{"type": "deletePlan"}]}\n```'
    envelope = _parse_envelope(text)
    assert envelope['reply'] == 'Hi'
    assert envelope['actions'] == [{'type': 'deletePlan'}]


def test_parse_envelope_falls_back_to_raw_text_on_malformed_json():
    text = 'This is not JSON at all.'
    envelope = _parse_envelope(text)
    assert envelope == {'reply': 'This is not JSON at all.', 'actions': []}


def test_parse_envelope_falls_back_when_actions_field_missing():
    text = '```json\n{"reply": "Hi"}\n```'
    envelope = _parse_envelope(text)
    assert envelope == {'reply': text.strip(), 'actions': []}


def _plan_with_two_parties(schoolbound_a=True, schoolbound_b=True, lonely_b=False):
    return {
        'dayPlans': {
            '1': {
                'dayOfWeekABCombo': {'uniqueNumber': 1},
                'parties': [
                    {
                        'driver': 'AB',
                        'time': 755,
                        'passengers': ['CD'],
                        'schoolbound': schoolbound_a,
                        'isLonelyDriver': False,
                    },
                    {
                        'driver': 'EF',
                        'time': 800,
                        'passengers': [],
                        'schoolbound': schoolbound_b,
                        'isLonelyDriver': lonely_b,
                    },
                ],
            }
        }
    }


def test_validate_move_passenger_accepts_same_direction_non_lonely_target():
    plan = _plan_with_two_parties()
    action = {
        'type': 'movePassenger',
        'dayUniqueNumber': 1,
        'passenger': 'CD',
        'fromParty': {'driver': 'AB', 'time': 755},
        'toParty': {'driver': 'EF', 'time': 800},
    }
    assert _validate_move_passenger(action, plan) is True


def test_validate_move_passenger_rejects_direction_mismatch():
    plan = _plan_with_two_parties(schoolbound_a=True, schoolbound_b=False)
    action = {
        'type': 'movePassenger',
        'dayUniqueNumber': 1,
        'passenger': 'CD',
        'fromParty': {'driver': 'AB', 'time': 755},
        'toParty': {'driver': 'EF', 'time': 800},
    }
    assert _validate_move_passenger(action, plan) is False


def test_validate_move_passenger_rejects_lonely_driver_target():
    plan = _plan_with_two_parties(lonely_b=True)
    action = {
        'type': 'movePassenger',
        'dayUniqueNumber': 1,
        'passenger': 'CD',
        'fromParty': {'driver': 'AB', 'time': 755},
        'toParty': {'driver': 'EF', 'time': 800},
    }
    assert _validate_move_passenger(action, plan) is False


def test_validate_move_passenger_rejects_passenger_not_in_source_party():
    plan = _plan_with_two_parties()
    action = {
        'type': 'movePassenger',
        'dayUniqueNumber': 1,
        'passenger': 'ZZ',
        'fromParty': {'driver': 'AB', 'time': 755},
        'toParty': {'driver': 'EF', 'time': 800},
    }
    assert _validate_move_passenger(action, plan) is False


def test_capacity_batch_allows_swap_that_nets_out():
    # Both cars have 2 seats (1 passenger each), already full.
    plan = {
        'dayPlans': {
            '1': {
                'dayOfWeekABCombo': {'uniqueNumber': 1},
                'parties': [
                    {'driver': 'AB', 'time': 755, 'passengers': ['CD'], 'schoolbound': True, 'isLonelyDriver': False},
                    {'driver': 'EF', 'time': 800, 'passengers': ['GH'], 'schoolbound': True, 'isLonelyDriver': False},
                ],
            }
        }
    }
    members = [{'initials': 'AB', 'numberOfSeats': 2}, {'initials': 'EF', 'numberOfSeats': 2}]
    actions = [
        {'type': 'movePassenger', 'dayUniqueNumber': 1, 'passenger': 'CD',
         'fromParty': {'driver': 'AB', 'time': 755}, 'toParty': {'driver': 'EF', 'time': 800}},
        {'type': 'movePassenger', 'dayUniqueNumber': 1, 'passenger': 'GH',
         'fromParty': {'driver': 'EF', 'time': 800}, 'toParty': {'driver': 'AB', 'time': 755}},
    ]
    assert _drop_capacity_violating_move_passengers(actions, plan, members) == actions


def test_capacity_batch_drops_when_net_result_overfills_a_car():
    # AB has 2 seats (capacity for 1 passenger), already has CD; adding GH
    # without removing anyone overfills the car.
    plan = {
        'dayPlans': {
            '1': {
                'dayOfWeekABCombo': {'uniqueNumber': 1},
                'parties': [
                    {'driver': 'AB', 'time': 755, 'passengers': ['CD'], 'schoolbound': True, 'isLonelyDriver': False},
                    {'driver': 'EF', 'time': 800, 'passengers': ['GH'], 'schoolbound': True, 'isLonelyDriver': False},
                ],
            }
        }
    }
    members = [{'initials': 'AB', 'numberOfSeats': 2}, {'initials': 'EF', 'numberOfSeats': 2}]
    actions = [
        {'type': 'movePassenger', 'dayUniqueNumber': 1, 'passenger': 'GH',
         'fromParty': {'driver': 'EF', 'time': 800}, 'toParty': {'driver': 'AB', 'time': 755}},
        {'type': 'deletePlan'},
    ]
    assert _drop_capacity_violating_move_passengers(actions, plan, members) == [{'type': 'deletePlan'}]


def test_validate_actions_drops_invalid_move_passenger_keeps_others():
    plan = _plan_with_two_parties(lonely_b=True)
    actions = [
        {
            'type': 'movePassenger',
            'dayUniqueNumber': 1,
            'passenger': 'CD',
            'fromParty': {'driver': 'AB', 'time': 755},
            'toParty': {'driver': 'EF', 'time': 800},
        },
        {'type': 'deletePlan'},
    ]
    validated = _validate_actions(actions, plan)
    assert validated == [{'type': 'deletePlan'}]
