# Shared configuration for cleanup scripts

TOKEN_FILE = "token.json"
LOGS_DIR = "logs"
PROTECTED_ACCOUNTS_FILE = "protected_accounts.json"
NON_FOLLOWER_CANDIDATES_FILE = "non_follower_candidates.json"

# Safe defaults
DRY_RUN_DEFAULT = True
REQUEST_DELAY_SECONDS_DEFAULT = 2.0
MAX_USERS_TO_PROCESS_DEFAULT = 5
MAX_TWEETS_TO_PROCESS_DEFAULT = 5
STOP_ON_RATE_LIMIT_DEFAULT = True

# Analysis / pagination settings
MAX_RESULTS_PER_PAGE = 1000

# Built-in fallback protected accounts
DEFAULT_KEEP_USERNAMES = {"akinooola"}
DEFAULT_KEEP_USER_IDS = set()