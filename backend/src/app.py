"""
Flask application for Carpool Time backend service.
"""
import base64
import io
import json
import logging
import os
import queue
import threading
import uuid
import zipfile
from collections import defaultdict
from datetime import datetime

import assistant_service
import config
import export_service
import requests
import user_settings
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from models import Member
from timetable_service import TimetableService
from utils import parse_date_yymmdd

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(name)s - %(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('backend_debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# The plan-generation engine logs its reasoning (model size, solve status,
# objective value, etc.) at length via the "solver_service" logger. That
# rationale is also fed to the AI assistant (see assistant_service.PLAN_LOG_PATH)
# so it can explain why the plan looks the way it does, so it's split into its
# own file rather than mixed in with the rest of the app's logging noise.
_plan_log_handler = logging.FileHandler(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plan_creation.log')
)
_plan_log_handler.setFormatter(logging.Formatter('[%(name)s - %(levelname)s] %(message)s'))
_solver_logger = logging.getLogger('solver_service')
_solver_logger.propagate = False
_solver_logger.setLevel(logging.DEBUG)
_solver_logger.addHandler(_plan_log_handler)
_solver_logger.addHandler(logging.StreamHandler())

# Loads the repo-root .env (searched for by walking up from this file), which
# holds GITHUB_ISSUE_CREATION used by the feedback endpoint below.
load_dotenv()

# Applies any user-edited settings (see /api/v1/settings below) saved from a
# previous run on top of the config.py defaults.
user_settings.load_and_apply()

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Plan generation with the CP-SAT engine can run for minutes, so it is exposed as
# a cancellable streaming job: /api/v1/drivingplan/stream emits progress and
# /api/v1/drivingplan/stop asks a running job for its current best solution.
# Maps job id -> the stop event the solver watches. Entries are removed when the
# stream ends, so a stop request for a finished job is simply a 404.
_plan_jobs = {}
_plan_jobs_lock = threading.Lock()


@app.route('/api/v1/check', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    
    Returns:
        JSON response with status
    """
    logger.info(f"Health check request from {request.remote_addr}")
    return jsonify(True), 200


@app.route('/api/v1/settings', methods=['GET'])
def get_settings():
    """
    Current values of the user-editable settings (WebUntis connection +
    plan generation parameters), for the frontend Preferences dialog.
    """
    return jsonify(user_settings.get_current()), 200


@app.route('/api/v1/settings', methods=['PUT'])
def update_settings():
    """
    Update one or more user-editable settings. Persists to disk (see
    user_settings.py) and applies immediately, no restart required.

    Expected JSON payload: a partial or full object of
    {WEBUNTIS_SERVER, WEBUNTIS_SCHOOL, TIME_TOLERANCE_MINUTES,
     MAX_DRIVES_FULLTIME, MAX_DRIVES_PARTTIME}.

    Returns:
        JSON response with the full set of current settings after the update
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        updated = user_settings.update(data)
        logger.info(f"Settings updated: {list(data.keys())}")
        return jsonify(updated), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/v1/suggestedreferencedate', methods=['POST'])
def suggested_reference_date():
    """
    Suggest a default reference date for the UI: the next date (today
    included) that falls in an A week, per the school's own week numbering.

    Expected JSON payload:
    {
        "username": "...",
        "hash": "..."  // Base64 encoded password
    }

    Returns:
        JSON response with the suggested date, or an error if WebUntis
        couldn't be reached (the frontend should fail silently and let the
        user pick a date manually).
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        for field in ['username', 'hash']:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        username = data['username']
        password = base64.b64decode(data['hash']).decode('utf-8')

        with TimetableService() as timetable_service:
            connected = timetable_service.connect(username, password)
            if not connected:
                return jsonify({'error': 'Could not connect to WebUntis'}), 502

            suggested_date = timetable_service.get_suggested_reference_date()

        return jsonify({'referenceDate': suggested_date.strftime('%Y%m%d')}), 200

    except Exception as e:
        logger.error(f"Error suggesting reference date: {str(e)}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/v1/membertimetable', methods=['POST'])
def member_timetable_detail():
    """
    Get a detailed, per-(weekday, A/B) breakdown of a single member's
    WebUntis schedule, including which periods were excluded and why, and
    any custom preference override - so the UI can explain why a member
    starts/leaves at a given time.

    Expected JSON payload:
    {
        "person": {...},  // Member object
        "scheduleReferenceStartDate": "20251223",  // YYYYMMDD format
        "username": "...",
        "hash": "..."  // Base64 encoded password
    }

    Returns:
        JSON response with the member's timetable detail
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        required_fields = ['person', 'scheduleReferenceStartDate', 'username', 'hash']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        try:
            member = Member.from_dict(data['person'])
        except Exception as e:
            logger.error(f"Error parsing member: {str(e)}")
            return jsonify({'error': f'Invalid member data: {str(e)}'}), 400

        try:
            date_value = data['scheduleReferenceStartDate']
            if isinstance(date_value, int):
                date_value = str(date_value)
            start_date = parse_date_yymmdd(date_value)
        except Exception as e:
            logger.error(f"Error parsing date: {str(e)}")
            return jsonify({'error': 'Invalid date format. Expected YYYYMMDD'}), 400

        username = data['username']
        password = base64.b64decode(data['hash']).decode('utf-8')

        with TimetableService() as timetable_service:
            connected = timetable_service.connect(username, password)
            if not connected:
                return jsonify({'error': 'Could not connect to WebUntis'}), 502

            detail = timetable_service.get_member_timetable_detail(member, start_date)

        return jsonify(detail), 200

    except Exception as e:
        logger.error(f"Error getting member timetable detail: {str(e)}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/v1/drivingplan', methods=['POST'])
def calculate_drivingplan():
    """
    Calculate driving plan endpoint (blocking, no progress reporting).

    Prefer /api/v1/drivingplan/stream: the CP-SAT engine needs minutes to prove
    a plan optimal, so this endpoint deliberately cuts the search short (see
    config.SOLVER_BLOCKING_MAX_TIME_SECONDS) and returns a good-but-unproven
    plan instead of holding the request open.
    
    Expected JSON payload:
    {
        "persons": [...],  // Array of member objects
        "scheduleReferenceStartDate": "20251223",  // YYYYMMDD format
        "username": "...",
        "hash": "..."  // Base64 encoded password
    }
    
    Returns:
        JSON response with driving plan
    """
    try:
        # Parse request
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        required_fields = ['persons', 'scheduleReferenceStartDate', 'username', 'hash']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Extract and decode password
        username = data['username']
        password = base64.b64decode(data['hash']).decode('utf-8')
        
        # Call core business logic
        driving_plan = calculate_driving_plan_logic(
            persons_data=data['persons'],
            start_date_str=data['scheduleReferenceStartDate'],
            username=username,
            password=password
        )
        
        # Convert to JSON and return
        response = driving_plan.to_dict()
        logger.info("Successfully calculated driving plan")
        return jsonify(response), 200
    
    except ValueError as e:
        # Validation errors from business logic
        logger.error(f"Validation error: {str(e)}")
        return jsonify({'error': str(e)}), 400
        
    except Exception as e:
        logger.error(f"Error calculating driving plan: {str(e)}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/v1/drivingplan/stream', methods=['POST'])
def calculate_drivingplan_stream():
    """
    Same as /api/v1/drivingplan, but streams progress while it works and can be
    stopped early. Finding a *provably optimal* plan takes minutes, so the UI
    needs to show what the solver has achieved so far and let the user settle
    for it.

    Expects the same JSON payload as /api/v1/drivingplan.

    Streams newline-delimited JSON, one object per line:
    {"type": "job", "jobId": "...",                       exactly once, first
     "noImprovementSeconds": 10.0}
    {"type": "status", "phase": "...", "message": "..."}  phase changes
    {"type": "progress", "metrics": {...}}                each improving solution
    {"type": "solved", "stats": {...}}                    how the solve ended
    {"type": "heartbeat"}                                 keeps the stream alive
    {"type": "final", "plan": {...}}                      exactly once, last
    {"type": "error", "message": "..."}                   instead of "final"

    Pass the jobId to /api/v1/drivingplan/stop to cut the search short and get
    the best plan found so far.
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    for field in ['persons', 'scheduleReferenceStartDate', 'username', 'hash']:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    try:
        password = base64.b64decode(data['hash']).decode('utf-8')
    except Exception:
        return jsonify({'error': 'Invalid hash: expected base64-encoded password'}), 400

    persons_data = data['persons']
    start_date_str = data['scheduleReferenceStartDate']
    username = data['username']

    job_id = uuid.uuid4().hex
    stop_event = threading.Event()
    with _plan_jobs_lock:
        _plan_jobs[job_id] = stop_event

    events = queue.Queue()
    DONE = object()

    def worker():
        try:
            driving_plan = calculate_driving_plan_logic(
                persons_data=persons_data,
                start_date_str=start_date_str,
                username=username,
                password=password,
                progress=events.put,
                stop_event=stop_event,
            )
            events.put({'type': 'final', 'plan': driving_plan.to_dict()})
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            events.put({'type': 'error', 'message': str(e)})
        except Exception as e:
            logger.error(f"Error calculating driving plan: {str(e)}", exc_info=True)
            events.put({'type': 'error', 'message': f'Internal server error: {str(e)}'})
        finally:
            events.put(DONE)

    def generate():
        yield json.dumps({
            'type': 'job',
            'jobId': job_id,
            # How long without an improving solution the client should wait before
            # auto-stopping. Reported rather than applied server-side so the UI owns
            # the countdown and can be switched off mid-solve; see config's note.
            'noImprovementSeconds': config.SOLVER_STOP_AFTER_NO_IMPROVEMENT_SECONDS,
        }) + '\n'
        thread = threading.Thread(target=worker, daemon=True, name=f'plan-{job_id[:8]}')
        thread.start()
        try:
            while True:
                try:
                    event = events.get(timeout=config.PLAN_STREAM_HEARTBEAT_SECONDS)
                except queue.Empty:
                    yield json.dumps({'type': 'heartbeat'}) + '\n'
                    continue
                if event is DONE:
                    break
                yield json.dumps(event) + '\n'
        finally:
            # Whether we finished or the client disconnected mid-stream, the job is
            # no longer stoppable, so drop it rather than leaking the registry entry.
            with _plan_jobs_lock:
                _plan_jobs.pop(job_id, None)
            # Nobody is left to receive a plan, and the client is the only thing
            # enforcing the no-improvement cutoff, so without this a disconnected
            # solve would keep a core busy until SOLVER_MAX_TIME_SECONDS. Harmless
            # on the normal path: the solve is already finished by then.
            stop_event.set()

    return Response(generate(), mimetype='application/x-ndjson')


@app.route('/api/v1/drivingplan/stop', methods=['POST'])
def stop_drivingplan():
    """
    Ask a running /api/v1/drivingplan/stream job to stop searching and return the
    best plan it has found so far. The plan still arrives on the original stream
    as a normal "final" event.

    Expected JSON payload: {"jobId": "..."}
    """
    data = request.get_json(silent=True) or {}
    job_id = data.get('jobId')
    if not job_id:
        return jsonify({'error': 'Missing required field: jobId'}), 400

    with _plan_jobs_lock:
        stop_event = _plan_jobs.get(job_id)

    if stop_event is None:
        return jsonify({'error': 'Unknown or already finished job'}), 404

    stop_event.set()
    logger.info(f"Stop requested for plan job {job_id}")
    return jsonify({'stopped': True}), 200


def _run_plan_engine(members, progress=None, stop_event=None):
    """Run the CP-SAT solver engine (solver_service.py) over `members`."""
    from solver_service import SolverInfeasibleError, SolverService

    solver = SolverService(
        progress_callback=(lambda metrics: progress({'type': 'progress', 'metrics': metrics}))
        if progress else None,
        stop_event=stop_event,
        # Without a progress sink the caller can't watch or interrupt the solve, so
        # cap it well short of the streaming endpoint's budget.
        max_time_in_seconds=None if progress else config.SOLVER_BLOCKING_MAX_TIME_SECONDS,
        # A streaming client enforces the no-improvement cutoff itself (it counts
        # down to it and can switch it off mid-solve), so a server-side timer here
        # would race the user's choice. Callers without a progress sink can do
        # neither, so they keep the config default.
        stop_after_no_improvement_seconds=(
            None if progress else config.SOLVER_STOP_AFTER_NO_IMPROVEMENT_SECONDS
        ),
    )
    try:
        plan = solver.calculate_driving_plan(members)
    except SolverInfeasibleError as e:
        raise ValueError(f"No feasible driving plan found: {e}") from e

    if progress:
        progress({'type': 'solved', 'stats': _solve_stats_payload(solver.last_solve_stats)})
    return plan


def _solve_stats_payload(stats):
    """JSON-safe view of SolverService.last_solve_stats for the progress stream."""
    return {
        'status': stats.get('status'),
        'wallTimeSeconds': stats.get('wallTime'),
        'solutionCount': stats.get('solutionCount'),
        'stoppedByUser': stats.get('stopped'),
        'provenOptimal': stats.get('status') == 'OPTIMAL',
        'metrics': stats.get('metrics'),
    }


def calculate_driving_plan_logic(persons_data, start_date_str, username, password,
                                 progress=None, stop_event=None):
    """
    Core business logic for calculating driving plan.
    Separated from HTTP layer to allow direct invocation.
    
    Args:
        persons_data: List of person dictionaries
        start_date_str: Date string in YYYYMMDD format
        username: WebUntis username
        password: WebUntis password (decoded)
        progress: Optional callable taking a JSON-serializable event dict, used
            by the streaming endpoint to report phases and intermediate solver
            solutions. None for the plain (blocking) endpoint.
        stop_event: Optional threading.Event; when set, the solver returns the
            best plan it has found so far instead of continuing to optimize.
    
    Returns:
        DrivingPlan object
        
    Raises:
        ValueError: If validation fails
        Exception: For other errors
    """
    # Parse members
    members = []
    for person_data in persons_data:
        try:
            member = Member.from_dict(person_data)
            members.append(member)
        except Exception as e:
            logger.error(f"Error parsing member: {str(e)}")
            raise ValueError(f'Invalid member data: {str(e)}')
    
    if not members:
        raise ValueError('No valid members provided')
    
    # Parse reference date
    try:
        date_value = start_date_str
        # Convert integer to string if needed
        if isinstance(date_value, int):
            date_value = str(date_value)
        start_date = parse_date_yymmdd(date_value)

    except ValueError as e:
        raise
    except Exception as e:
        logger.error(f"Error parsing date: {str(e)}")
        raise ValueError('Invalid date format. Expected YYYYMMDD')
    
    logger.info(f"Calculating driving plan for {len(members)} members starting {start_date.strftime('%Y-%m-%d')}")

    if progress:
        progress({'type': 'status', 'phase': 'timetables',
                  'message': 'Fetching timetables from WebUntis'})

    # Connect to timetable provider and get schedules
    with TimetableService() as timetable_service:
        # Try to connect to WebUntis
        try:
            connected = timetable_service.connect(username, password)
            if not connected:
                logger.warning("Failed to connect to WebUntis, using mock timetables")
        except Exception as e:
            logger.warning(f"WebUntis connection error: {str(e)}, using mock timetables")
        
        # Get timetables for all members
        try:
            timetable_service.get_timetables_for_members(members, start_date)
        except Exception as e:
            logger.error(f"Error getting timetables: {str(e)}")
            raise e

    if config.CAPTURE_PLAN_INPUTS:
        _capture_plan_input(members, start_date_str)

    if progress:
        progress({'type': 'status', 'phase': 'solving',
                  'message': 'Searching for the best driving plan'})

    # Calculate driving plan
    driving_plan = _run_plan_engine(members, progress=progress, stop_event=stop_event)
    
    # Print to console for debugging
    _print_to_console(driving_plan, members)
    
    return driving_plan


def _capture_plan_input(members, start_date_str):
    """
    Dump the members (incl. custom prefs) and their resolved WebUntis
    timetables to config.CAPTURE_DIR, so real-world plan-generation inputs
    can be replayed offline against the algorithm without needing WebUntis
    credentials again. Deliberately excludes username/password/hash.
    """
    try:
        capture_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), config.CAPTURE_DIR)
        os.makedirs(capture_dir, exist_ok=True)

        timetables = {}
        for member in members:
            timetables[member.initials] = {
                str(day_num): {
                    'startTime': t.start_time,
                    'endTime': t.end_time,
                    'scheduledStartTime': t.scheduled_start_time,
                    'scheduledEndTime': t.scheduled_end_time,
                    'isPresent': t.is_present,
                }
                for day_num, t in member.timetable.items()
            }

        capture = {
            'capturedAt': datetime.now().isoformat(),
            'scheduleReferenceStartDate': start_date_str,
            'persons': [
                {
                    'firstName': m.first_name,
                    'lastName': m.last_name,
                    'initials': m.initials,
                    'numberOfSeats': m.number_of_seats,
                    'isPartTime': m.is_part_time,
                    'customDays': {str(k): v.to_dict() for k, v in m.custom_days.items()},
                }
                for m in members
            ],
            'timetables': timetables,
        }

        filename = f"drivingplan-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.json"
        with open(os.path.join(capture_dir, filename), 'w') as f:
            json.dump(capture, f, indent=2)
        logger.info(f"Captured plan input to {filename}")
    except Exception as e:
        logger.warning(f"Failed to capture plan input: {str(e)}")


def _print_to_console(driving_plan, members):
    logger.debug("Driving Plan Results:")
    logger.debug(f"Total days: {len(driving_plan.day_plans)}")
    
    # Group members by drive count
    drive_count_groups = defaultdict(list)
    for m in members:
        drive_count_groups[m.drive_count].append(f"{m.first_name} ({m.initials})")
    
    logger.debug("Drive counts:")
    for count in sorted(drive_count_groups.keys()):
        members_str = ', '.join(drive_count_groups[count])
        logger.debug(f" - {count}: {members_str}")
    logger.debug("")
    
    # Day plans sorted by day number
    sorted_days = sorted(driving_plan.day_plans.items(), key=lambda x: x[0])
    
    for day_num, day_plan in sorted_days:
        logger.debug(f"=== Day {day_num} ===")
        
        # Schoolbound parties
        schoolbound = [p for p in day_plan.parties if p.schoolbound]
        if schoolbound:
            logger.debug("  Schoolbound:")
            for party in sorted(schoolbound, key=lambda p: p.time or 0):
                time_str = f"{party.time:04d}" if party.time else "----"
                passengers_part = f" | Passengers: {', '.join(party.passengers)}" if party.passengers else ""
                logger.debug(f"    {time_str} | Driver: {party.driver}{'*' if party.is_designated_driver else ''}{passengers_part}")
        
        # Homebound parties
        homebound = [p for p in day_plan.parties if not p.schoolbound]
        if homebound:
            logger.debug("  Homebound:")
            for party in sorted(homebound, key=lambda p: p.time or 0):
                time_str = f"{party.time:04d}" if party.time else "----"
                passengers_part = f" | Passengers: {', '.join(party.passengers)}" if party.passengers else ""
                logger.debug(f"    {time_str} | Driver: {party.driver}{'*' if party.is_designated_driver else ''}{passengers_part}")
        
        logger.debug("")


@app.route('/api/v1/feedback', methods=['POST'])
def create_feedback_issue():
    """
    Create a GitHub issue from user-submitted feedback.

    Expected JSON payload:
    {
        "title": "...",
        "description": "...",
        "label": "bug" | "question" | "enhancement"
    }

    Returns:
        JSON response with the created issue's URL
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        title = (data.get('title') or '').strip()
        description = (data.get('description') or '').strip()
        label = data.get('label')

        if not title:
            return jsonify({'error': 'Title is required'}), 400
        if label not in config.GITHUB_FEEDBACK_LABELS:
            return jsonify({'error': 'Invalid label'}), 400

        github_token = os.environ.get('GITHUB_ISSUE_CREATION')
        if not github_token:
            logger.error("GITHUB_ISSUE_CREATION is not configured; cannot create feedback issue")
            return jsonify({'error': 'GITHUB_ISSUE_CREATION is not configured'}), 500

        response = requests.post(
            f'https://api.github.com/repos/{config.GITHUB_FEEDBACK_REPO}/issues',
            headers={
                'Authorization': f'Bearer {github_token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28',
            },
            json={
                'title': title,
                'body': description,
                'labels': ['user feedback', label],
                'assignees': [config.GITHUB_FEEDBACK_ASSIGNEE],
            },
            timeout=10,
        )

        if response.status_code != 201:
            logger.error(f"GitHub issue creation failed ({response.status_code}): {response.text}")
            return jsonify({'error': 'Failed to create GitHub issue'}), 502

        issue = response.json()
        logger.info(f"Created feedback issue: {issue.get('html_url')}")
        return jsonify({'issueUrl': issue.get('html_url')}), 201

    except Exception as e:
        logger.error(f"Error creating feedback issue: {str(e)}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/v1/assistant/spinner-verbs', methods=['GET'])
def assistant_spinner_verbs():
    """
    Returns the list of whimsical status messages shown in the UI while the
    assistant is thinking (backed by assistant/harry-potter-spinning-verbs.txt).
    """
    try:
        path = os.path.join(os.path.dirname(__file__), 'assistant', 'harry-potter-spinning-verbs.txt')
        with open(path, 'r', encoding='utf-8') as f:
            verbs = [line.strip() for line in f if line.strip()]
        return jsonify(verbs), 200
    except Exception as e:
        logger.error(f"Error reading spinner verbs: {str(e)}", exc_info=True)
        return jsonify([]), 200


@app.route('/api/v1/assistant/chat', methods=['POST'])
def assistant_chat():
    """
    Chat with the AI assistant about the current members/driving plan, and
    optionally receive proposed actions (member/plan edits) for the
    frontend to apply.

    Expected JSON payload:
    {
        "messages": [{"role": "user" | "assistant", "content": "..."}, ...],
        "context": {
            "members": [...],
            "plan": {...} | null,
            "uiContext": {...}
        }
    }

    Streams the response as newline-delimited JSON, one object per line:
    {"type": "delta", "text": "..."} for incremental reply text,
    {"type": "thinking_delta", "text": "..."} / {"type": "tool_call",
    "name": "..."} for intermediate model activity (safe to ignore), followed
    by exactly one {"type": "final", "reply": "...", "actions": [...]}, or
    {"type": "error", "message": "..."} if something went wrong.
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    messages = data.get('messages')
    if not isinstance(messages, list) or not messages:
        return jsonify({'error': 'Missing required field: messages'}), 400

    context = data.get('context') or {}

    def generate():
        try:
            for event in assistant_service.ask_stream(messages, context):
                yield json.dumps(event) + '\n'
        except Exception as e:
            logger.error(f"Error in assistant chat: {str(e)}", exc_info=True)
            yield json.dumps({'type': 'error', 'message': str(e)}) + '\n'

    return Response(generate(), mimetype='application/x-ndjson')


@app.route('/api/v1/export/png', methods=['POST'])
def export_png():
    """
    Render the current plan's Week A and Week B tables (as shown by the
    frontend's isolated /export view) in a headless browser and return them
    as PNG screenshots.

    Expected JSON payload:
    {
        "members": [...],
        "plan": {...},
        "referenceDate": "2026-09-09" | null,
        "showDesignatedDriver": bool,
        "showSoloDriver": bool,
        "darkMode": bool
    }

    Returns:
        A single ZIP file (image/png entries "driving-plan-week-a.png" and
        "driving-plan-week-b.png"). Both images are bundled into one download
        rather than returned separately, because browsers throttle/drop
        automatically-triggered downloads that fire back-to-back without a
        fresh user gesture in between - a single download avoids that
        entirely.
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        for field in ['members', 'plan']:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        frontend_host = request.host.split(':')[0]
        frontend_origin = f'http://{frontend_host}:{config.FRONTEND_PORT}'

        images = export_service.render_week_screenshots(
            members=data['members'],
            plan=data['plan'],
            reference_date=data.get('referenceDate'),
            show_designated_driver=bool(data.get('showDesignatedDriver')),
            show_solo_driver=bool(data.get('showSoloDriver')),
            dark_mode=bool(data.get('darkMode')),
            frontend_origin=frontend_origin,
        )

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('driving-plan-week-a.png', images['weekA'])
            zf.writestr('driving-plan-week-b.png', images['weekB'])

        return Response(buffer.getvalue(), mimetype='application/zip')

    except Exception as e:
        logger.error(f"Error exporting plan as PNG: {str(e)}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    logger.info(f"Starting Carpool Time backend service on port {config.PORT}")
    app.run(debug=config.DEBUG, port=config.PORT, host='0.0.0.0', threaded=True)
