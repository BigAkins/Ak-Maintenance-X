# Ak Maintenance X

A Python automation tool for securely inspecting and managing X (Twitter) account activity using the X API.

This project uses OAuth 2.0 Authorization Code Flow with PKCE and is designed as a **safety-first automation system** for managing account activity such as likes and follows.

---

## Features

- OAuth 2.0 PKCE authentication
- Secure token-based API access
- Read-only account inspection
- Dry-run cleanup previews (no changes made)
- Bulk unlike tweets (with logging)
- Bulk unfollow accounts (with protection rules)
- Non-follower detection and targeted unfollowing
- Protected account filtering (external config)
- CSV logging for all actions
- Resume support from previous logs
- Rate-limit protection (stop on 429)

---

## Project Structure

```
ak-maintenance-x/
├── auth_test.py
├── get_me.py
├── account_inspector.py
├── dry_run_cleanup.py
├── bulk_unlike.py
├── bulk_unfollow.py
├── find_non_followers.py
├── bulk_unfollow_non_followers.py
├── cleanup_config.py
├── cleanup_helpers.py
├── protected_accounts.example.json
├── PROJECT_ARCHITECTURE.md
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## How It Works

This project follows a structured, safe workflow:

```
authenticate
→ inspect account data
→ generate candidate actions
→ preview with dry-run
→ execute in small batches
→ log results
→ resume if needed
```

---

## Quick Start

### 1. Install dependencies

```
pip install -r requirements.txt
```

### 2. Create environment file

```
cp .env.example .env
```

Add your X API credentials.

### 3. Authenticate

```
python auth_test.py
```

### 4. Verify authentication

```
python get_me.py
```

---

## Main Workflows

### Read-only inspection

```
python account_inspector.py
python dry_run_cleanup.py
```

### Bulk unlike tweets

```
python bulk_unlike.py
```

### Bulk unfollow (general)

```
python bulk_unfollow.py
```

### Find non-followers

```
python find_non_followers.py
```

### Unfollow non-followers (from reviewed file)

```
python bulk_unfollow_non_followers.py
```

---

## Safety Features

- Dry-run mode enabled by default
- Small batch-size limits
- Request delay between API calls
- Protected account filtering via config file
- Candidate file verification before actions
- CSV logging of all actions
- Resume support using previous logs
- Automatic stop on rate limit (429)

---

## Configuration Files

### `.env`
Stores your API credentials (never commit this file).

### `protected_accounts.example.json`
Public-safe example file.

### `protected_accounts.json`
Local private file for protected usernames and IDs.

Example:

```
{
  "keep_usernames": [
    "akinooola"
  ],
  "keep_user_ids": []
}
```

### `non_follower_candidates.json`
Generated file containing reviewed non-follower accounts.

---

## Documentation

See `PROJECT_ARCHITECTURE.md` for a deeper breakdown of:
- system design
- script responsibilities
- data flow
- safety mechanisms

---

## Author

Akinola Ogunbiyi  
Former Division-I athlete transitioning into software engineering, DevOps, and automation tooling.