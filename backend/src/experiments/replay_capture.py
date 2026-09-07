"""
Replay a single captured plan-generation input (see app._capture_plan_input)
through the algorithm, without needing WebUntis at all - the capture already
holds the resolved per-member timetables.

Usage: python replay_capture.py <capture.json> <output_plan.json>

Each invocation is meant to run in its own fresh interpreter (see
run_batch.py) so that Python's per-process string-hash randomization varies
run to run, the same way it does across real backend restarts - that's the
one source of run-to-run non-determinism in the algorithm (iteration order
of `set`-typed member collections), since no other randomness is involved.
"""
import json
import sys
from pathlib import Path

backend_src = Path(__file__).parent.parent
sys.path.insert(0, str(backend_src))

from algorithm_service import AlgorithmService  # type: ignore
from models import CustomDay, Member, Timetable  # type: ignore


def build_members(capture: dict) -> list:
    members = []
    for person in capture['persons']:
        member = Member.from_dict(person)
        member.id = None
        member_timetables = capture['timetables'].get(member.initials, {})
        member.timetable = {
            int(day_num): Timetable(
                member_initials=member.initials,
                day_number=int(day_num),
                start_time=t['startTime'],
                end_time=t['endTime'],
                scheduled_start_time=t['scheduledStartTime'],
                scheduled_end_time=t['scheduledEndTime'],
                is_present=t['isPresent'],
            )
            for day_num, t in member_timetables.items()
        }
        members.append(member)
    return members


def main():
    if len(sys.argv) != 3:
        print("Usage: python replay_capture.py <capture.json> <output_plan.json>")
        sys.exit(1)

    capture_path, output_path = sys.argv[1], sys.argv[2]

    with open(capture_path) as f:
        capture = json.load(f)

    members = build_members(capture)

    algorithm = AlgorithmService()
    driving_plan = algorithm.calculate_driving_plan(members)

    with open(output_path, 'w') as f:
        json.dump(driving_plan.to_dict(), f)


if __name__ == '__main__':
    main()
