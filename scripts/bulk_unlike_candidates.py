import csv
import json
import os
import time
from datetime import datetime

import requests

try:
    from scripts._bootstrap import bootstrap_project_root
except ModuleNotFoundError:
    from _bootstrap import bootstrap_project_root

bootstrap_project_root()

from ak_maintenance_x.cleanup_config import (
    LOGS_DIR,
    LIKE_CANDIDATES_FILE,
    DRY_RUN_DEFAULT,
    REQUEST_DELAY_SECONDS_DEFAULT,
    MAX_TWEETS_TO_PROCESS_DEFAULT,
    STOP_ON_RATE_LIMIT_DEFAULT,
    AUTO_WAIT_ON_RATE_LIMIT_DEFAULT,
    MAX_RATE_LIMIT_RETRIES_DEFAULT,
)
from ak_maintenance_x.cleanup_helpers import (
    load_access_token,
    get_profile,
    make_headers,
)
from ak_maintenance_x.cleanup_rate_limits import (
    maybe_wait_from_success_response,
    handle_rate_limit_http_error,
)

UNLIKE_URL = "https://api.x.com/2/users/{user_id}/likes/{tweet_id}"

DRY_RUN = DRY_RUN_DEFAULT
REQUEST_DELAY_SECONDS = REQUEST_DELAY_SECONDS_DEFAULT
MAX_TWEETS_TO_PROCESS = MAX_TWEETS_TO_PROCESS_DEFAULT
STOP_ON_RATE_LIMIT = STOP_ON_RATE_LIMIT_DEFAULT
AUTO_WAIT_ON_RATE_LIMIT = AUTO_WAIT_ON_RATE_LIMIT_DEFAULT
MAX_RATE_LIMIT_RETRIES = MAX_RATE_LIMIT_RETRIES_DEFAULT

LOG_FILE_PREFIX = "bulk_unlike_candidates_log_"


def load_like_candidates_file():
    try:
        with open(LIKE_CANDIDATES_FILE, "r", encoding="utf-8") as file:
            candidate_data = json.load(file)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"{LIKE_CANDIDATES_FILE} not found. Run find_likes_by_date.py first."
        ) from exc

    candidates = candidate_data.get("like_candidates", [])
    summary = candidate_data.get("summary", {})
    authenticated_user = candidate_data.get("authenticated_user", {})

    return authenticated_user, summary, candidates


def unlike_tweet(access_token, user_id, tweet_id):
    url = UNLIKE_URL.format(user_id=user_id, tweet_id=tweet_id)

    response = requests.delete(
        url,
        headers=make_headers(access_token),
        timeout=30,
    )
    response.raise_for_status()
    return response


def ensure_logs_dir():
    os.makedirs(LOGS_DIR, exist_ok=True)


def build_log_file_path():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(LOGS_DIR, f"{LOG_FILE_PREFIX}{timestamp}.csv")


def write_log_header(csv_writer):
    csv_writer.writerow(
        [
            "timestamp",
            "tweet_id",
            "created_at",
            "author_id",
            "status",
            "details",
        ]
    )


def log_result(csv_writer, tweet_id, created_at, author_id, status, details):
    csv_writer.writerow(
        [
            datetime.now().isoformat(),
            tweet_id,
            created_at,
            author_id,
            status,
            details,
        ]
    )


def get_successfully_processed_tweet_ids():
    if not os.path.exists(LOGS_DIR):
        return set()

    successful_ids = set()

    for filename in os.listdir(LOGS_DIR):
        if not filename.startswith(LOG_FILE_PREFIX) or not filename.endswith(".csv"):
            continue

        file_path = os.path.join(LOGS_DIR, filename)

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row.get("status") == "SUCCESS":
                        successful_ids.add(str(row.get("tweet_id", "")).strip())
        except Exception as error:
            print(f"[WARNING] Could not read log file {filename}: {error}")

    return successful_ids


def filter_out_already_processed_candidates(candidates, processed_tweet_ids):
    remaining_candidates = []
    skipped_count = 0

    for candidate in candidates:
        tweet_id = str(candidate.get("id", "")).strip()
        if tweet_id in processed_tweet_ids:
            skipped_count += 1
            continue
        remaining_candidates.append(candidate)

    return remaining_candidates, skipped_count


def preview_candidates(
    summary,
    original_candidates,
    remaining_candidates,
    skipped_count,
    limit=MAX_TWEETS_TO_PROCESS_DEFAULT,
    dry_run=DRY_RUN_DEFAULT,
):
    print("\n--- BULK UNLIKE CANDIDATES PREVIEW ---")
    print(f"Eligible like candidates in file: {len(original_candidates)}")
    print(f"Already successfully processed from logs: {skipped_count}")
    print(f"Remaining candidates after resume filter: {len(remaining_candidates)}")
    print(f"Configured to process up to {limit} tweets.")

    if summary:
        print("\nCandidate file summary:")
        for key, value in summary.items():
            print(f"- {key}: {value}")

    candidates_to_process = remaining_candidates[:limit]

    if not candidates_to_process:
        print("\nNo remaining like candidates found to process.")
        return candidates_to_process

    print("\nLike candidates that would be processed:")
    for candidate in candidates_to_process[:10]:
        print(
            f"- tweet_id={candidate.get('id')} | "
            f"created_at={candidate.get('created_at')} | "
            f"text={candidate.get('text', '')[:80]}"
        )

    if dry_run:
        print("\nDRY_RUN is ON. No likes will actually be removed.")

    return candidates_to_process


def process_unlikes(
    access_token,
    user_id,
    candidates_to_process,
    log_file_path,
    dry_run=DRY_RUN_DEFAULT,
    request_delay_seconds=REQUEST_DELAY_SECONDS_DEFAULT,
    stop_on_rate_limit=STOP_ON_RATE_LIMIT_DEFAULT,
    auto_wait_on_rate_limit=AUTO_WAIT_ON_RATE_LIMIT_DEFAULT,
    max_rate_limit_retries=MAX_RATE_LIMIT_RETRIES_DEFAULT,
):
    success_count = 0
    failure_count = 0
    stopped_due_to_rate_limit = False

    with open(log_file_path, "w", newline="", encoding="utf-8") as log_file:
        csv_writer = csv.writer(log_file)
        write_log_header(csv_writer)

        for candidate in candidates_to_process:
            tweet_id = candidate.get("id", "unknown_id")
            created_at = candidate.get("created_at", "")
            author_id = candidate.get("author_id", "")

            if dry_run:
                print(f"[DRY RUN] Would unlike tweet {tweet_id}")
                log_result(
                    csv_writer,
                    tweet_id,
                    created_at,
                    author_id,
                    "DRY_RUN",
                    "Preview only - no action taken",
                )
                continue

            retry_count = 0

            while True:
                try:
                    response = unlike_tweet(access_token, user_id, tweet_id)
                    result = response.json()

                    print(f"[SUCCESS] Unliked tweet {tweet_id}: {result}")
                    log_result(
                        csv_writer,
                        tweet_id,
                        created_at,
                        author_id,
                        "SUCCESS",
                        str(result),
                    )
                    success_count += 1

                    maybe_wait_from_success_response(
                        response,
                        action_label=f"bulk_unlike_candidates tweet {tweet_id}",
                        auto_wait=auto_wait_on_rate_limit,
                    )
                    break

                except requests.HTTPError as error:
                    print(f"[FAILED] Could not unlike tweet {tweet_id}: {error}")

                    waited = handle_rate_limit_http_error(
                        error,
                        action_label=f"bulk_unlike_candidates tweet {tweet_id}",
                        auto_wait=auto_wait_on_rate_limit,
                    )

                    if waited and retry_count < max_rate_limit_retries:
                        retry_count += 1
                        print(f"[RETRY] Retrying unlike for tweet {tweet_id} after rate-limit wait...")
                        continue

                    log_result(
                        csv_writer,
                        tweet_id,
                        created_at,
                        author_id,
                        "FAILED",
                        str(error),
                    )
                    failure_count += 1

                    if error.response is not None and error.response.status_code == 429:
                        stopped_due_to_rate_limit = True
                        if stop_on_rate_limit:
                            print("\n[STOP] Rate limit persisted. Stopping run early.")
                            return success_count, failure_count, stopped_due_to_rate_limit
                    break

            time.sleep(request_delay_seconds)

    return success_count, failure_count, stopped_due_to_rate_limit


def run_bulk_unlike_candidates(
    dry_run=DRY_RUN_DEFAULT,
    limit=MAX_TWEETS_TO_PROCESS_DEFAULT,
    request_delay_seconds=REQUEST_DELAY_SECONDS_DEFAULT,
    stop_on_rate_limit=STOP_ON_RATE_LIMIT_DEFAULT,
    auto_wait_on_rate_limit=AUTO_WAIT_ON_RATE_LIMIT_DEFAULT,
    max_rate_limit_retries=MAX_RATE_LIMIT_RETRIES_DEFAULT,
):
    """Execute the like-candidate workflow and return a summary dict."""
    print("Loading access token...")
    access_token = load_access_token()

    print("Verifying authenticated user...")
    live_profile = get_profile(access_token)
    user_id = live_profile["id"]

    print("\nAuthenticated as:")
    print(f"Name: {live_profile['name']}")
    print(f"Username: @{live_profile['username']}")
    print(f"User ID: {user_id}")

    print("\nLoading like candidates file...")
    file_user, summary, original_candidates = load_like_candidates_file()

    print("\nCandidate file created for:")
    print(f"Name: {file_user.get('name')}")
    print(f"Username: @{file_user.get('username')}")
    print(f"User ID: {file_user.get('id')}")

    if str(file_user.get("id")) != str(user_id):
        raise ValueError(
            "Candidate file user ID does not match the currently authenticated user."
        )

    print("\nChecking prior logs for resume support...")
    processed_tweet_ids = get_successfully_processed_tweet_ids()
    remaining_candidates, skipped_count = filter_out_already_processed_candidates(
        original_candidates,
        processed_tweet_ids,
    )

    candidates_to_process = preview_candidates(
        summary,
        original_candidates,
        remaining_candidates,
        skipped_count,
        limit=limit,
        dry_run=dry_run,
    )

    ensure_logs_dir()
    log_file_path = build_log_file_path()

    print(f"\nLog file will be written to: {log_file_path}")

    success_count, failure_count, stopped_due_to_rate_limit = process_unlikes(
        access_token,
        user_id,
        candidates_to_process,
        log_file_path,
        dry_run=dry_run,
        request_delay_seconds=request_delay_seconds,
        stop_on_rate_limit=stop_on_rate_limit,
        auto_wait_on_rate_limit=auto_wait_on_rate_limit,
        max_rate_limit_retries=max_rate_limit_retries,
    )

    print("\n--- BULK UNLIKE CANDIDATES SUMMARY ---")
    if dry_run:
        print("Mode: DRY RUN")
        print(f"Previewed {len(candidates_to_process)} like candidates.")
        print("No changes were made.")
    else:
        print("Mode: LIVE")
        print(f"Successfully unliked: {success_count}")
        print(f"Failed to unlike: {failure_count}")

        if stopped_due_to_rate_limit:
            print("Run stopped early because of rate limiting.")
            print("You can rerun later and resume from the remaining candidates.")

    print(f"Log saved to: {log_file_path}")

    workflow_summary = {
        "candidate_file": LIKE_CANDIDATES_FILE,
        "candidate_file_summary": summary,
        "original_candidates": len(original_candidates),
        "remaining_candidates": len(remaining_candidates),
        "skipped_from_resume": skipped_count,
        "request_delay_seconds": request_delay_seconds,
        "stop_on_rate_limit": stop_on_rate_limit,
        "auto_wait_on_rate_limit": auto_wait_on_rate_limit,
        "max_rate_limit_retries": max_rate_limit_retries,
    }

    return {
        "profile": live_profile,
        "mode": "DRY RUN" if dry_run else "LIVE",
        "processed": len(candidates_to_process),
        "success": success_count,
        "failed": failure_count,
        "dry_run": dry_run,
        "success_count": success_count,
        "failure_count": failure_count,
        "stopped_due_to_rate_limit": stopped_due_to_rate_limit,
        "log_file_path": log_file_path,
        "summary": workflow_summary,
    }


def main():
    run_bulk_unlike_candidates()


if __name__ == "__main__":
    main()
