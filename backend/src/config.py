# Configuration file for Carpool Time Backend

# WebUntis Configuration
WEBUNTIS_SERVER = "https://ngw-wilhelmshaven.webuntis.com"
WEBUNTIS_SCHOOL = ""
WEBUNTIS_USERAGENT = "github-carpoolparty-python"

# Cache Configuration
CACHE_DIR = "./cache_dir"
CACHE_TTL_SECONDS = None # 3600  # 1 hour - timetables rarely change during the day

# Algorithm Configuration
TIME_TOLERANCE_MINUTES = 30  # Maximum time deviation to group members together
MAX_DRIVES_FULLTIME = 4  # Maximum drives for full-time members in 2-week cycle
MAX_DRIVES_PARTTIME = 2  # Maximum drives for part-time members in 2-week cycle

# Server Configuration
PORT = 1338
DEBUG = True
