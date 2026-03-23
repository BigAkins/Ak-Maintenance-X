# Project Architecture

## Overview

Ak Maintenance X is a Python-based automation system for inspecting and managing account activity on X using the X API.

The project is designed around a **safety-first workflow pipeline**:

1. authenticate
2. inspect data
3. generate candidates
4. preview actions in dry-run mode
5. execute actions in controlled batches
6. log results for traceability and resume support

This system is built to behave like a **production-grade tool**, where mistakes could impact real user data.

---

## Core Design Principles

### 1. Separation of concerns
Each script and module has a single responsibility:
- analysis scripts (read-only)
- action scripts (mutating operations)
- shared helpers (reusable logic)
- configuration (centralized settings)

---

### 2. Safety-first defaults
All workflows are designed to prevent accidental data loss:
- dry-run mode enabled by default
- small batch sizes
- explicit `--live` flag required for execution

---

### 3. Shared configuration
Common settings are centralized in:

```
ak_maintenance_x/cleanup_config.py
```

Examples:
- default batch sizes
- request delays
- rate-limit retry behavior
- protected accounts file
- log directory paths

---

### 4. Shared helpers
Reusable logic lives in:

```
ak_maintenance_x/cleanup_helpers.py
```

Examples:
- loading access tokens
- building request headers
- fetching authenticated user info
- pagination helpers
- candidate file validation
- username normalization

---

### 5. Rate-limit awareness
The system is designed to handle real-world API constraints:
- request delays between calls
- automatic retry handling
- optional auto-wait behavior
- stop-on-429 protection

Core logic lives in:

```
ak_maintenance_x/cleanup_rate_limits.py
```

---

### 6. Logging and resume support
All action workflows:
- write structured CSV logs
- track success vs failure
- support resuming from previous runs

This prevents:
- duplicate actions
- wasted API calls
- inconsistent state

---

### 7. CLI-driven architecture
All workflows are exposed through a centralized CLI:

```
main.py
```

Features:
- workflow registry
- direct commands + aliases
- argument validation
- JSON output mode
- shell autocomplete support

---

## Project Structure

```
Ak-Maintenance-X/
│
├── ak_maintenance_x/
│   ├── cleanup_config.py
│   ├── cleanup_helpers.py
│   ├── cleanup_rate_limits.py
│   └── workflows.py
│
├── scripts/
│   ├── auth_test.py
│   ├── get_me.py
│   ├── account_inspector.py
│   ├── dry_run_cleanup.py
│   ├── find_non_followers.py
│   ├── find_reposts.py
│   ├── find_likes_by_date.py
│   ├── find_posts_by_date.py
│   ├── bulk_unlike.py
│   ├── bulk_unlike_candidates.py
│   ├── bulk_unfollow.py
│   ├── bulk_unfollow_non_followers.py
│   ├── bulk_unrepost.py
│   └── bulk_delete_posts_by_date.py
│
├── logs/
├── main.py
├── .env
└── PROJECT_ARCHITECTURE.md
```

---

## Workflow Types

### 1. Authentication

#### `auth_test.py`
Handles OAuth 2.0 PKCE authentication.

Output:
- `token.json`

---

### 2. Utility / Inspection

#### `get_me.py`
Verifies authentication and displays account identity.

#### `account_inspector.py`
Read-only inspection of:
- profile info
- likes
- following

#### `dry_run_cleanup.py`
Preview-only cleanup simulation.

---

### 3. Analysis Workflows (Read-Only)

These scripts generate candidate files for review.

#### `find_non_followers.py`
- compares following vs followers
- filters protected accounts
- outputs:
  - `non_follower_candidates.json`

#### `find_reposts.py`
- scans user timeline
- filters reposts by date
- outputs:
  - `repost_candidates.json`

#### `find_likes_by_date.py`
- fetches liked tweets
- filters by created_at date
- outputs:
  - `like_candidates.json`

#### `find_posts_by_date.py`
- fetches user tweets
- filters by date range
- supports excluding:
  - reposts
  - replies
- outputs:
  - `post_delete_candidates.json`

---

### 4. Action Workflows (Mutating)

These scripts perform account changes.

#### `bulk_unlike.py`
- directly unlikes tweets

#### `bulk_unlike_candidates.py`
- unlikes from reviewed candidate file

#### `bulk_unfollow.py`
- unfollows selected accounts

#### `bulk_unfollow_non_followers.py`
- unfollows reviewed non-followers
- verifies candidate file ownership
- supports resume via logs

#### `bulk_unrepost.py`
- removes reposts from candidate file
- rate-limit aware
- resumable

#### `bulk_delete_posts_by_date.py`
- deletes posts from candidate file
- supports filtering logic from analysis step

---

## Data Flow

```
auth_test.py
    ↓
token.json
    ↓
inspection / analysis scripts
    ↓
candidate files (.json)
    ↓
action workflows
    ↓
logs/*.csv
```

---

## Safety Pipeline

Every action follows:

```
analyze → generate candidates → review → dry-run → execute → log → resume
```

This ensures:
- visibility before action
- control during execution
- recoverability after failure

---

## Why This Architecture Matters

This project is designed to mirror real-world engineering systems:

- handles external API constraints
- protects against destructive actions
- tracks state across runs
- separates read vs write workflows
- prioritizes user safety over speed

It is not just a collection of scripts — it is a **controlled automation system**.