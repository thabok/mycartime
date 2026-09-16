"""
Replay a single captured plan-generation input (see app._capture_plan_input)
through the CP-SAT solver, without needing WebUntis at all - the capture
already holds the resolved per-member timetables.

Usage: python replay_capture.py <capture.json> <output_plan.json>
           [--max-seconds N] [--no-improvement-seconds N|none]

Each invocation is meant to run in its own fresh interpreter (see
run_batch.py) so that Python's per-process string-hash randomization varies
run to run, the same way it does across real backend restarts - that's the
one source of run-to-run non-determinism in model *building* (iteration order
of `set`-typed member collections), since CP-SAT itself doesn't depend on it.
"""
import json
import sys
from pathlib import Path

backend_src = Path(__file__).parent.parent
sys.path.insert(0, str(backend_src))

from models import CustomDay, Member, Timetable  # type: ignore

_UNSET = object()  # distinguishes "flag not passed" (use config default) from "--no-improvement-seconds none"


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


def build_engine(max_seconds=None, no_improvement_seconds=_UNSET):
    """Return a SolverService instance exposing calculate_driving_plan(members)."""
    from solver_service import SolverService  # type: ignore
    kwargs = {}
    if no_improvement_seconds is not _UNSET:
        kwargs['stop_after_no_improvement_seconds'] = no_improvement_seconds
    return SolverService(max_time_in_seconds=max_seconds, **kwargs)


def _take_option(args: list, name: str):
    """Pop `--name value` out of args, returning the value or None."""
    if name not in args:
        return None
    idx = args.index(name)
    if idx + 1 >= len(args):
        raise SystemExit(f"{name} needs a value")
    value = args[idx + 1]
    del args[idx:idx + 2]
    return value


def main():
    args = sys.argv[1:]
    max_seconds = _take_option(args, '--max-seconds')
    max_seconds = float(max_seconds) if max_seconds else None

    no_improvement_seconds = _take_option(args, '--no-improvement-seconds')
    if no_improvement_seconds is None:
        no_improvement_seconds = _UNSET
    elif no_improvement_seconds.lower() == 'none':
        no_improvement_seconds = None
    else:
        no_improvement_seconds = float(no_improvement_seconds)

    if len(args) != 2:
        print("Usage: python replay_capture.py <capture.json> <output_plan.json> "
              "[--max-seconds N] [--no-improvement-seconds N|none]")
        sys.exit(1)

    capture_path, output_path = args

    with open(capture_path) as f:
        capture = json.load(f)

    members = build_members(capture)

    driving_plan = build_engine(max_seconds, no_improvement_seconds).calculate_driving_plan(members)

    with open(output_path, 'w') as f:
        json.dump(driving_plan.to_dict(), f)


if __name__ == '__main__':
    main()
