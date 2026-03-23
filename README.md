# Ak Maintenance X

A safety-first automation system for inspecting and managing X (Twitter) account activity using the X API.

Built as part of my athlete-to-tech transition, this project focuses on **real-world automation, API design, and safe batch processing systems**.

---

## What This Project Does

Ak Maintenance X helps you:

- Analyze your account (likes, follows, reposts, posts)
- Identify cleanup targets (non-followers, old likes, reposts)
- Preview changes safely (dry-run mode)
- Execute bulk actions (unlike, unfollow, unrepost, delete)
- Handle rate limits, logging, and resume safely

---

## Key Features

- OAuth 2.0 PKCE authentication
- Modular Python architecture
- CLI interface with aliases (like a real tool)
- Dry-run mode by default (safety-first)
- Batch processing with limits and delays
- Resume support via logs
- Rate-limit handling (429 protection + retry logic)
- External protected account config
- JSON + human-readable output modes
- Shell autocomplete support (argcomplete)

---

## Architecture

The system follows a **safe workflow pipeline**:

```
authenticate
→ inspect data
→ generate candidates
→ preview (dry-run)
→ execute (batched + safe)
→ log results
→ resume if needed
```

For a deeper breakdown, see `PROJECT_ARCHITECTURE.md`.

---

## Project Structure

```
Ak-Maintenance-X/
│
├── ak_maintenance_x/      # Core package (helpers, config, rate limits, workflows)
├── scripts/               # Individual workflow scripts
├── logs/                  # CSV logs (generated)
├── main.py                # CLI entrypoint
├── .env                   # API credentials (local only)
├── README.md
└── PROJECT_ARCHITECTURE.md
```

---

## Setup

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
python scripts/auth_test.py
```

### 4. Verify

```
python main.py whoami
```

---

## CLI Usage

### List workflows

```
python main.py list
```

### Example commands

```
python main.py whoami
python main.py inspect-account
python main.py non-followers
python main.py reposts --start-time 2026-03-31T00:00:00Z --end-time 2026-04-03T00:00:00Z

python main.py unrepost --dry-run --limit 5
python main.py delete-posts --dry-run --limit 10
```

### JSON mode (for automation)

```
python main.py whoami --json
```

---

## Safety Features

This project is built **not to mess up your account**:

- Dry-run mode ON by default
- Batch limits enforced
- Request delays between API calls
- Protected accounts filtering
- Candidate file verification
- CSV logs for every action
- Resume support from logs
- Rate-limit detection + retry handling

---

## Example Workflow

```
python main.py non-followers
→ generates candidate file

review file

python main.py unfollow-non-followers --dry-run
→ preview

python main.py unfollow-non-followers --live
→ execute safely
```

---

## What I Learned

- How to design safe automation systems
- How to work with real-world APIs (OAuth, pagination, rate limits)
- CLI design and developer experience
- Structuring scalable Python projects
- Building tools with real-world consequences

---

## Author

Akinola Ogunbiyi  
Former Division I athlete → Software Engineer

Building tools, systems, and automation while documenting the journey.

---

## ⚠️ Disclaimer

This project is for educational and personal use.  
Use responsibly and respect platform policies.