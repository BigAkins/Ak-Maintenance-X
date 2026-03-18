# Project Architecture

## Overview

Ak Maintenance X is a Python automation project for inspecting and managing account activity on X using the X API.

The project is designed around a safety-first workflow:

1. authenticate
2. inspect data
3. generate candidates
4. preview actions in dry-run mode
5. execute actions in controlled batches
6. log results for traceability and resume support

---

## Core Design Principles

### 1. Separation of concerns
Each script has one main job.

### 2. Safe defaults
Scripts default to dry-run mode and small batch sizes.

### 3. Shared configuration
Common settings live in `cleanup_config.py`.

### 4. Shared helpers
Reusable utility functions live in `cleanup_helpers.py`.

### 5. Logging and resume support
Action scripts write CSV logs and can use prior results to avoid repeating successful work.

---

## File Responsibilities

### `cleanup_config.py`
Shared configuration values for the project.

Examples:
- token file name
- logs directory
- dry-run defaults
- request delay defaults
- batch size defaults
- protected accounts file name

---

### `cleanup_helpers.py`
Shared helper functions used by multiple scripts.

Examples:
- loading access tokens
- building authorization headers
- fetching the authenticated user profile
- normalizing usernames
- loading protected account rules

---

### `auth_test.py`
Handles OAuth authentication with X and saves a token locally.

Purpose:
- verify authentication works
- save token data for later scripts

Output:
- `token.json`

---

### `get_me.py`
Tests the authenticated session by calling the current-user endpoint.

Purpose:
- verify the saved token works
- confirm the logged-in account

---

### `account_inspector.py`
Read-only inspection script.

Purpose:
- inspect profile info
- inspect liked tweets
- inspect followed accounts

Safety:
- makes no account changes

---

### `dry_run_cleanup.py`
Preview-only cleanup script.

Purpose:
- show what would be unliked or unfollowed
- validate cleanup logic before live actions

Safety:
- makes no account changes

---

### `bulk_unlike.py`
Batch unlike workflow.

Purpose:
- preview liked tweets
- unlike tweets in small batches
- log every result

Safety features:
- dry-run mode
- batch cap
- request delay
- CSV logging

---

### `bulk_unfollow.py`
Generic batch unfollow workflow.

Purpose:
- unfollow selected followed accounts
- apply protected account filtering
- log every result

Safety features:
- protected accounts config
- dry-run mode
- batch cap
- request delay
- CSV logging

---

### `find_non_followers.py`
Read-only non-follower analysis workflow.

Purpose:
- fetch all following pages
- fetch all follower pages
- compare user IDs
- remove protected accounts
- save a reviewed candidate list

Output:
- `non_follower_candidates.json`

Safety:
- makes no account changes

---

### `bulk_unfollow_non_followers.py`
Specialized batch unfollow workflow for reviewed non-follower candidates.

Purpose:
- load the saved candidate list
- verify the file matches the authenticated user
- preview or unfollow candidates
- stop on rate limit
- resume using previous success logs

Safety features:
- dry-run mode
- batch cap
- request delay
- stop on 429
- resume support from logs
- candidate file user-ID verification

---

## Data Flow

```text
auth_test.py
    ↓
token.json
    ↓
get_me.py / account_inspector.py / dry_run_cleanup.py
    ↓
find_non_followers.py
    ↓
non_follower_candidates.json
    ↓
bulk_unfollow_non_followers.py
    ↓
logs/*.csv