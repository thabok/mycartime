"""
Flask application for Carpool Time backend service.
"""
import base64
import json
import logging
import os
from collections import defaultdict

import assistant_service
import config
import requests
from algorithm_service import AlgorithmService
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

# Loads the repo-root .env (searched for by walking up from this file), which
# holds GITHUB_ISSUE_CREATION used by the feedback endpoint below.
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

GITHUB_FEEDBACK_REPO = 'thabok/mycartime'
GITHUB_FEEDBACK_LABELS = {'bug', 'question', 'enhancement'}
GITHUB_FEEDBACK_ASSIGNEE = 'thabok'


@app.route('/api/v1/check', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    
    Returns:
        JSON response with status
    """
    logger.info(f"Health check request from {request.remote_addr}")
    return jsonify(True), 200


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


@app.route('/api/v1/drivingplan', methods=['POST'])
def calculate_drivingplan():
    """
    Calculate driving plan endpoint.
    
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

def calculate_driving_plan_logic(persons_data, start_date_str, username, password):
    """
    Core business logic for calculating driving plan.
    Separated from HTTP layer to allow direct invocation.
    
    Args:
        persons_data: List of person dictionaries
        start_date_str: Date string in YYYYMMDD format
        username: WebUntis username
        password: WebUntis password (decoded)
    
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
    
    # Calculate driving plan
    algorithm = AlgorithmService()
    driving_plan = algorithm.calculate_driving_plan(members)
    
    # Print to console for debugging
    _print_to_console(driving_plan, members)
    
    return driving_plan


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
        if label not in GITHUB_FEEDBACK_LABELS:
            return jsonify({'error': 'Invalid label'}), 400

        github_token = os.environ.get('GITHUB_ISSUE_CREATION')
        if not github_token:
            logger.error("GITHUB_ISSUE_CREATION is not configured; cannot create feedback issue")
            return jsonify({'error': 'GITHUB_ISSUE_CREATION is not configured'}), 500

        response = requests.post(
            f'https://api.github.com/repos/{GITHUB_FEEDBACK_REPO}/issues',
            headers={
                'Authorization': f'Bearer {github_token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28',
            },
            json={
                'title': title,
                'body': description,
                'labels': ['user feedback', label],
                'assignees': [GITHUB_FEEDBACK_ASSIGNEE],
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
