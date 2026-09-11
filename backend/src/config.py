# Configuration file for Carpool Time Backend
import os

import paths

# WebUntis Configuration
WEBUNTIS_SERVER = "https://ngw-wilhelmshaven.webuntis.com"
WEBUNTIS_SCHOOL = ""
WEBUNTIS_USERAGENT = "github-carpoolparty-python"

# Template for the "open timetable" link handed to the frontend, built from
# WEBUNTIS_SERVER so there's a single source of truth for the school's domain.
SCHEDULE_URL_TEMPLATE = f"{WEBUNTIS_SERVER}/timetable/teacher?date=DATE&entityId=TEACHER_ID"

# Cache Configuration
CACHE_DIR = paths.data_path("cache_dir")
CACHE_TTL_SECONDS = None # 3600  # 1 hour - timetables rarely change during the day

# Room id -> name overrides for rooms that WebUntis's getRooms() doesn't
# return (e.g. duty-only locations used for break supervision), so periods
# referencing them still get a display name instead of "Unknown room".
ROOM_NAME_FALLBACKS = {
    131: "Bus",
}

# Algorithm Configuration
TIME_TOLERANCE_MINUTES = 30  # Maximum time deviation to group members together
MAX_DRIVES_FULLTIME = 4  # Maximum drives for full-time members in 2-week cycle
MAX_DRIVES_PARTTIME = 3  # Maximum drives for part-time members in 2-week cycle

# Server Configuration
# Both are overridable so the Tauri shell can hand the sidecar a free port and
# keep it bound to the loopback interface, while development keeps the defaults.
PORT = int(os.environ.get('BACKEND_PORT', 1338))
HOST = os.environ.get('BACKEND_HOST', '0.0.0.0')
# Flask debug mode (interactive debugger + auto-reload) - defaults to off so a
# real deployment doesn't accidentally ship the debugger unless FLASK_DEBUG=true
# is set explicitly. Enabled by default for local dev via run.sh/start.sh.
DEBUG = False # os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'

# The Vite dev server port for the frontend (see frontend/vite.config.ts).
FRONTEND_PORT = 8080

# Origins allowed to call this backend. The packaged app serves the frontend
# from the Tauri webview's own scheme (tauri://localhost on macOS/Linux,
# http://tauri.localhost on Windows); the localhost entries keep the Vite dev
# server working against an unpackaged backend.
ALLOWED_ORIGINS = [
    "tauri://localhost",
    "http://tauri.localhost",
    f"http://localhost:{FRONTEND_PORT}",
    f"http://127.0.0.1:{FRONTEND_PORT}",
]

# AI Assistant Configuration
# Both are set through the Settings dialog. The API key falls back to the
# environment variable of the same name, which is how development runs supply
# it; the CLI path falls back to whatever `claude` is on PATH.
ANTHROPIC_API_KEY = ""
CLAUDE_CLI_PATH = ""
ASSISTANT_MODEL = "claude-sonnet-4-6"
ASSISTANT_MAX_TOKENS = 2000
ASSISTANT_CLI_TIMEOUT_SECONDS = 60

# When True, every /api/v1/drivingplan request dumps its members + resolved
# WebUntis timetables (no credentials) to CAPTURE_DIR, for offline replay of
# real-world inputs against the solver (see backend/src/experiments/).
CAPTURE_PLAN_INPUTS = False
CAPTURE_DIR = paths.data_path("captures")

# ---------------------------------------------------------------------------
# Plan engine (solver_service.py, an OR-Tools CP-SAT model)
# ---------------------------------------------------------------------------
# See doc/ALGORITHM_EVOLUTION.md for why this replaced the earlier five-phase
# greedy heuristic.

# Stop a solve after this many seconds without an improving solution, and serve
# the best one found so far. On a real ~20-member set CP-SAT reaches the optimum
# in roughly 20s and needs about twice that to prove nothing better exists, so
# this cuts the proof phase short once progress has clearly stalled rather than
# making every request wait for a proof nobody asked for. Stopping here costs
# very little quality: on a real capture the plan at this cutoff was within one
# week-A/B mismatch of the proven optimum. Set to None to disable and rely
# solely on SOLVER_MAX_TIME_SECONDS / SOLVER_BLOCKING_MAX_TIME_SECONDS.
#
# The streaming endpoint does not use this timer itself - it reports this value
# to the client, which runs the countdown and calls /drivingplan/stop, so the UI
# can show how long is left and let the user switch the auto-stop off mid-solve
# without racing a server-side timer.
SOLVER_STOP_AFTER_NO_IMPROVEMENT_SECONDS = 10.0

# Wall-clock safety net for a single CP-SAT solve, on top of the no-improvement
# stall timeout above - this limit only exists so a pathological input can't
# hang a request forever even while still finding new improving solutions.
# Hitting it - like pressing Stop - yields the best solution found so far,
# which is good but not provably optimal, and (unlike an OPTIMAL result) not
# guaranteed to be reproducible.
SOLVER_MAX_TIME_SECONDS = 900.0

# Budget for the plain, non-streaming /api/v1/drivingplan endpoint. That caller
# can neither watch progress nor press Stop, so it gets a short budget rather
# than the full SOLVER_MAX_TIME_SECONDS: a good-but-unproven plan in seconds
# beats a provably optimal one after a request timeout. Clients that want the
# optimum should use /api/v1/drivingplan/stream.
SOLVER_BLOCKING_MAX_TIME_SECONDS = 20.0

# How often the solve thread checks whether the user pressed Stop. Small enough
# that Stop feels instant, large enough not to cost measurable solve time.
SOLVER_STOP_POLL_SECONDS = 0.2

# Fixed seed + single-threaded search is what makes CP-SAT's output
# reproducible run to run (see backend/test/test_determinism_solver.py).
SOLVER_RANDOM_SEED = 0

# Weights for the CP-SAT objective. The gaps between them are large enough
# that the terms behave lexicographically for realistic inputs (a single unit
# of a higher-priority term outweighs the worst possible total of all lower
# ones), which mirrors the composite ordering analyze_plans.py already uses to
# rank plans. The whole weighted sum has to stay inside CP-SAT's int64
# objective, which is what caps how many tiers there can be - solver_service
# logs a warning if an unusually large member set could break the ordering.
# Tune here rather than in solver_service.py.
#
# Note what is deliberately *absent*: there is no term rewarding fewer total
# drives or fewer cars on the road. A good plan is the one where the fewest
# members exceed their MAX_DRIVES - not the one with the least driving. Members
# driving noticeably less than their MAX_DRIVES is not a win, it is a source of
# friction within the group, so the solver is left indifferent between two plans
# that keep everyone inside their quota.
SOLVER_OBJECTIVE_WEIGHTS = {
    'overflow': 10_000_000_000_000_000,   # exceeding a member's max_drives
    'drives_despite_prefs': 10_000_000_000_000,  # driving on a drivingSkip day
    'over_6': 100_000_000_000,            # members driving more than 6x
    'over_5': 1_000_000_000,              # members driving more than 5x
    'over_4': 10_000_000,                 # members driving more than 4x
    'week_ab_mismatch': 1_000,            # weekdays driven in only one of the two weeks
    'week_ab_count_imbalance': 1,         # week A/B drive-count swing beyond the unavoidable 1
}

# ---------------------------------------------------------------------------
# Feedback endpoint (POST /api/v1/feedback in app.py)
# ---------------------------------------------------------------------------
GITHUB_FEEDBACK_REPO = 'thabok/mycartime'
GITHUB_FEEDBACK_LABELS = {'bug', 'question', 'enhancement'}
GITHUB_FEEDBACK_ASSIGNEE = 'thabok'

# How long the /api/v1/drivingplan/stream connection waits for a plan event
# before emitting a heartbeat, so the connection (and the UI's "still working"
# state) stays alive during the long stretch where CP-SAT is proving
# optimality without finding better solutions.
PLAN_STREAM_HEARTBEAT_SECONDS = 2.0
