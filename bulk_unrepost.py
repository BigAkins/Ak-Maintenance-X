import csv
import json
import os
import time
from datetime import datetime

import requests

from cleanup_config import (
    LOGS_DIR,
    REPOST_CANDIDATES_FILE,
    DRY_RUN_DEFAULT,
    REQUEST_DELAY_SECONDS_DEFAULT,
    MAX_TWEETS_TO_PROCESS_DEFAULT,
    STOP_ON_RATE_LIMIT_DEFAULT,
)
from cleanup_helpers import (
    load_access_token,
    get_profile,
    make_headers,
)

UNREPOST_URL = "https://api.x.com/2/users/{user_id}/retweets/{source_tweet_id}"

DRY_RUN = DRY_RUN_DEFAULT
REQUEST_DELAY_SECONDS = REQUEST_DELAY_SECONDS_DEFAULT
MAX_TWEETS_TO_PROCESS = MAX_TWEETS_TO_PROCESS_DEFAULT
STOP_ON_RATE_LIMIT = STOP_ON_RATE_LIMIT_DEFAULT

LOG_FILE_PREFIX = "bulk_unrepost_log_"


def load_repost_candidates_file():
    try:
        with open(REPOST_CANDIDATES_FILE, "r", encoding="utf-8") as file:
            candidate_data = json.load(file)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"{REPOST_CANDIDATES_FILE} not found. Run find_reposts.py first."
        ) from exc

    candidates = candidate_data.get("repost_candidates", [])
    summary = candidate_data.get("summary", {})
    authenticated_user = candidate_data.get("authenticated_user", {})

    return authenticated_user, summary, candidates


def unrepost_tweet(access_token, user_id, source_tweet_id):
    url = UNREPOST_URL.format(
        user_id=user_id,
        source_tweet_id=source_tweet_id,
    )

    response = requests.delete(
        url,
        headers=make_headers(access_token),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def ensure_logs_dir():
    os.makedirs(LOGS_DIR, exist_ok=True)


def build_log_file_path():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(LOGS_DIR, f"{LOG_FILE_PREFIX}{timestamp}.csv")


def write_log_header(csv_writer):
    csv_writer.writerow(
        [
            "timestamp",
            "repost_tweet_id",
            "source_tweet_id",
            "created_at",
            "status",
            "details",
        ]
    )


def log_result(csv_writer, repost_tweet_id, source_tweet_id, created_at, status, details):
    csv_writer.writerow(
        [
            datetime.now().isoformat(),
            repost_tweet_id,
            source_tweet_id,
            created_at,
            status,
            details,
        ]
    )


def get_successfully_processed_source_tweet_ids():
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
                        successful_ids.add(str(row.get("source_tweet_id", "")).strip())
        except Exception as error:
            print(f"[WARNING] Could not read log file {filename}: {error}")

    return successful_ids


def filter_out_already_processed_candidates(candidates, processed_source_tweet_ids):
    remaining_candidates = []
    skipped_count = 0

    for candidate in candidates:
        source_tweet_id = str(candidate.get("referenced_tweet_id", "")).strip()
        if source_tweet_id in processed_source_tweet_ids:
            skipped_count += 1
            continue
        remaining_candidates.append(candidate)

    return remaining_candidates, skipped_count


def preview_candidates(summary, original_candidates, remaining_candidates, skipped_count):
    print("\n--- BULK UNREPOST PREVIEW ---")
    print(f"Eligible repost candidates in file: {len(original_candidates)}")
    print(f"Already successfully processed from logs: {skipped_count}")
    print(f"Remaining candidates after resume filter: {len(remaining_candidates)}")
    print(f"Configured to process up to {MAX_TWEETS_TO_PROCESS} reposts.")

    if summary:
        print("\nCandidate file summary:")
        for key, value in summary.items():
            print(f"- {key}: {value}")

    candidates_to_process = remaining_candidates[:MAX_TWEETS_TO_PROCESS]

    if not candidates_to_process:
        print("\nNo remaining repost candidates found to process.")
        return candidates_to_process

    print("\nRepost candidates that would be processed:")
    for candidate in candidates_to_process:
        print(
            f"- repost_id={candidate.get('id')} | "
            f"source_tweet_id={candidate.get('referenced_tweet_id')} | "
            f"created_at={candidate.get('created_at')}"
        )

    if DRY_RUN:
        print("\nDRY_RUN is ON. No reposts will actually be removed.")

    return candidates_to_process


def process_unreposts(access_token, user_id, candidates_to_process, log_file_path):
    success_count = 0
    failure_count = 0
    stopped_due_to_rate_limit = False

    with open(log_file_path, "w", newline="", encoding="utf-8") as log_file:
        csv_writer = csv.writer(log_file)
        write_log_header(csv_writer)

        for candidate in candidates_to_process:
            repost_tweet_id = candidate.get("id", "unknown_id")
            source_tweet_id = candidate.get("referenced_tweet_id", "unknown_source_id")
            created_at = candidate.get("created_at", "")

            if DRY_RUN:
                print(f"[DRY RUN] Would unrepost source tweet {source_tweet_id}")
                log_result(
                    csv_writer,
                    repost_tweet_id,
                    source_tweet_id,
                    created_at,
                    "DRY_RUN",
                    "Preview only - no action taken",
                )
                continue

            try:
                result = unrepost_tweet(access_token, user_id, source_tweet_id)
                print(f"[SUCCESS] Unreposted source tweet {source_tweet_id}: {result}")
                log_result(
                    csv_writer,
                    repost_tweet_id,
                    source_tweet_id,
                    created_at,
                    "SUCCESS",
                    str(result),
                )
                success_count += 1

            except requests.HTTPError as error:
                status_code = None
                if error.response is not None:
                    status_code = error.response.status_code

                print(f"[FAILED] Could not unrepost source tweet {source_tweet_id}: {error}")
                log_result(
                    csv_writer,
                    repost_tweet_id,
                    source_tweet_id,
                    created_at,
                    "FAILED",
                    str(error),
                )
                failure_count += 1

                if STOP_ON_RATE_LIMIT and status_code == 429:
                    print("\n[STOP] Rate limit hit (429). Stopping run early to preserve progress.")
                    stopped_due_to_rate_limit = True
                    break

            time.sleep(REQUEST_DELAY_SECONDS)

    return success_count, failure_count, stopped_due_to_rate_limit


def main():
    print("Loading access token...")
    access_token = load_access_token()

    print("Verifying authenticated user...")
    live_profile = get_profile(access_token)
    user_id = live_profile["id"]

    print("\nAuthenticated as:")
    print(f"Name: {live_profile['name']}")
    print(f"Username: @{live_profile['username']}")
    print(f"User ID: {user_id}")

    print("\nLoading repost candidates file...")
    file_user, summary, original_candidates = load_repost_candidates_file()

    print("\nCandidate file created for:")
    print(f"Name: {file_user.get('name')}")
    print(f"Username: @{file_user.get('username')}")
    print(f"User ID: {file_user.get('id')}")

    if str(file_user.get("id")) != str(user_id):
        raise ValueError(
            "Candidate file user ID does not match the currently authenticated user."
        )

    print("\nChecking prior logs for resume support...")
    processed_source_tweet_ids = get_successfully_processed_source_tweet_ids()
    remaining_candidates, skipped_count = filter_out_already_processed_candidates(
        original_candidates,
        processed_source_tweet_ids,
    )

    candidates_to_process = preview_candidates(
        summary,
        original_candidates,
        remaining_candidates,
        skipped_count,
    )

    ensure_logs_dir()
    log_file_path = build_log_file_path()

    print(f"\nLog file will be written to: {log_file_path}")

    success_count, failure_count, stopped_due_to_rate_limit = process_unreposts(
        access_token,
        user_id,
        candidates_to_process,
        log_file_path,
    )

    print("\n--- BULK UNREPOST SUMMARY ---")
    if DRY_RUN:
        print("Mode: DRY RUN")
        print(f"Previewed {len(candidates_to_process)} repost candidates.")
        print("No changes were made.")
    else:
        print("Mode: LIVE")
        print(f"Successfully unreposted: {success_count}")
        print(f"Failed to unrepost: {failure_count}")

        if stopped_due_to_rate_limit:
            print("Run stopped early because of rate limiting.")
            print("You can rerun later and resume from the remaining candidates.")

    print(f"Log saved to: {log_file_path}")


if __name__ == "__main__":
    main()