# Token refresh settings

TOKEN_REFRESH_BUFFER_SECONDS = 300
TOKEN_URL = "https://api.x.com/2/oauth2/token"

# Shared configuration for cleanup scripts

TOKEN_FILE = "token.json"
LOGS_DIR = "logs"
PROTECTED_ACCOUNTS_FILE = "protected_accounts.json"
NON_FOLLOWER_CANDIDATES_FILE = "non_follower_candidates.json"
REPOST_CANDIDATES_FILE = "repost_candidates.json"
LIKE_CANDIDATES_FILE = "like_candidates.json"
POST_DELETE_CANDIDATES_FILE = "post_delete_candidates.json"

# Safe defaults
DRY_RUN_DEFAULT = True
REQUEST_DELAY_SECONDS_DEFAULT = 2.0
MAX_USERS_TO_PROCESS_DEFAULT = 5
MAX_TWEETS_TO_PROCESS_DEFAULT = 5
STOP_ON_RATE_LIMIT_DEFAULT = True

# Rate-limit handling
AUTO_WAIT_ON_RATE_LIMIT_DEFAULT = True
MAX_RATE_LIMIT_RETRIES_DEFAULT = 3
RATE_LIMIT_RESET_BUFFER_SECONDS_DEFAULT = 5

# Analysis / pagination settings
MAX_RESULTS_PER_PAGE = 1000
TIMELINE_MAX_RESULTS_PER_PAGE = 100
LIKED_TWEETS_MAX_RESULTS_PER_PAGE = 100

# Built-in fallback protected accounts
DEFAULT_KEEP_USERNAMES = {"akinooola"}
DEFAULT_KEEP_USER_IDS = set()