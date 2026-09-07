# Configuration file for Carpool Time Backend

# WebUntis Configuration
WEBUNTIS_SERVER = "https://ngw-wilhelmshaven.webuntis.com"
WEBUNTIS_SCHOOL = ""
WEBUNTIS_USERAGENT = "github-carpoolparty-python"

# Cache Configuration
CACHE_DIR = "./cache_dir"
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
EXACT_MATCH_TOLERANCE_MINUTES = 5  # Max deviation still treated as an "exact" time match (e.g. grouping passengers with an identical schedule)

# Server Configuration
PORT = 1338
DEBUG = True

# The Vite dev server port for the frontend (see frontend/vite.config.ts).
# Used by the PNG export endpoint to drive a headless browser against the
# live frontend app.
FRONTEND_PORT = 8080

# AI Assistant Configuration
ASSISTANT_MODEL = "claude-sonnet-4-6"
ASSISTANT_MAX_TOKENS = 2000
ASSISTANT_CLI_TIMEOUT_SECONDS = 60

# When True, every /api/v1/drivingplan request dumps its members + resolved
# WebUntis timetables (no credentials) to CAPTURE_DIR, for offline replay of
# real-world inputs against the algorithm (see backend/src/experiments/).
CAPTURE_PLAN_INPUTS = True
CAPTURE_DIR = "./captures"
