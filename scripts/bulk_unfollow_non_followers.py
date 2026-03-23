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
    NON_FOLLOWER_CANDIDATES_FILE,
    DRY_RUN_DEFAULT,
    REQUEST_DELAY_SECONDS_DEFAULT,
    MAX_USERS_TO_PROCESS_DEFAULT,
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

UNFOLLOW_URL = "https://api.x.com/2/users/{source_user_id}/following/{target_user_id}"

DRY_RUN = DRY_RUN_DEFAULT
REQUEST_DELAY_SECONDS = REQUEST_DELAY_SECONDS_DEFAULT
MAX_USERS_TO_PROCESS = MAX_USERS_TO_PROCESS_DEFAULT
STOP_ON_RATE_LIMIT = STOP_ON_RATE_LIMIT_DEFAULT
AUTO_WAIT_ON_RATE_LIMIT = AUTO_WAIT_ON_RATE_LIMIT_DEFAULT
MAX_RATE_LIMIT_RETRIES = MAX_RATE_LIMIT_RETRIES_DEFAULT

LOG_FILE_PREFIX = "bulk_unfollow_non_followers_log_"


def load_candidates_file():
    try:
        with open(NON_FOLLOWER_CANDIDATES_FILE, "r", encoding="utf-8") as file:
            candidate_data = json.load(file)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            "non_follower_candidates.json not found. Run find_non_followers.py first."
        ) from exc

    candidates = candidate_data.get("eligible_candidates", [])
    summary = candidate_data.get("summary", {})
    authenticated_user = candidate_data.get("authenticated_user", {})

    return authenticated_user, summary, candidates


def unfollow_user(access_token, source_user_id, target_user_id):
    url = UNFOLLOW_URL.format(
        source_user_id=source_user_id,
        target_user_id=target_user_id,
    )

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
            "target_user_id",
            "username",
            "name",
            "status",
            "details",
        ]
    )


def log_result(csv_writer, target_user_id, username, name, status, details):
    csv_writer.writerow(
        [
            datetime.now().isoformat(),
            target_user_id,
            username,
            name,
            status,
            details,
        ]
    )


def get_successfully_processed_user_ids():
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
                        successful_ids.add(str(row.get("target_user_id", "")).strip())
        except Exception as error:
            print(f"[WARNING] Could not read log file {filename}: {error}")

    return successful_ids


def filter_out_already_processed_candidates(candidates, processed_ids):
    remaining_candidates = []
    skipped_count = 0

    for user in candidates:
        user_id = str(user.get("id", "")).strip()
        if user_id in processed_ids:
            skipped_count += 1
            continue
        remaining_candidates.append(user)

    return remaining_candidates, skipped_count


def preview_candidates(
    summary,
    original_candidates,
    remaining_candidates,
    skipped_count,
    limit=MAX_USERS_TO_PROCESS,
    dry_run=DRY_RUN,
):
    print("\n--- NON-FOLLOWER UNFOLLOW PREVIEW ---")
    print(f"Eligible candidates in file: {len(original_candidates)}")
    print(f"Already successfully processed from logs: {skipped_count}")
    print(f"Remaining candidates after resume filter: {len(remaining_candidates)}")
    print(f"Configured to process up to {limit} accounts.")

    if summary:
        print("\nCandidate file summary:")
        for key, value in summary.items():
            print(f"- {key}: {value}")

    users_to_process = remaining_candidates[:limit]

    if not users_to_process:
        print("\nNo remaining eligible candidates found to process.")
        return users_to_process

    print("\nCandidates that would be processed:")
    for user in users_to_process:
        user_id = user.get("id", "unknown_id")
        username = user.get("username", "unknown_username")
        name = user.get("name", "unknown_name")
        print(f"- [{user_id}] @{username} ({name})")

    if dry_run:
        print("\nDRY_RUN is ON. No accounts will actually be unfollowed.")

    return users_to_process


def process_unfollows(
    access_token,
    source_user_id,
    users_to_process,
    log_file_path,
    dry_run=DRY_RUN,
    request_delay_seconds=REQUEST_DELAY_SECONDS,
    stop_on_rate_limit=STOP_ON_RATE_LIMIT,
    auto_wait_on_rate_limit=AUTO_WAIT_ON_RATE_LIMIT,
    max_rate_limit_retries=MAX_RATE_LIMIT_RETRIES,
):
    success_count = 0
    failure_count = 0
    stopped_due_to_rate_limit = False

    with open(log_file_path, "w", newline="", encoding="utf-8") as log_file:
        csv_writer = csv.writer(log_file)
        write_log_header(csv_writer)

        for user in users_to_process:
            target_user_id = user.get("id", "unknown_id")
            username = user.get("username", "unknown_username")
            name = user.get("name", "unknown_name")

            if dry_run:
                print(f"[DRY RUN] Would unfollow non-follower @{username} ({target_user_id})")
                log_result(
                    csv_writer,
                    target_user_id,
                    username,
                    name,
                    "DRY_RUN",
                    "Preview only - no action taken",
                )
                continue

            retry_count = 0

            while True:
                try:
                    response = unfollow_user(access_token, source_user_id, target_user_id)
                    result = response.json()

                    print(f"[SUCCESS] Unfollowed non-follower @{username} ({target_user_id}): {result}")
                    log_result(
                        csv_writer,
                        target_user_id,
                        username,
                        name,
                        "SUCCESS",
                        str(result),
                    )
                    success_count += 1

                    maybe_wait_from_success_response(
                        response,
                        action_label=f"bulk_unfollow_non_followers user {target_user_id}",
                        auto_wait=auto_wait_on_rate_limit,
                    )
                    break

                except requests.HTTPError as error:
                    print(f"[FAILED] Could not unfollow non-follower @{username} ({target_user_id}): {error}")

                    waited = handle_rate_limit_http_error(
                        error,
                        action_label=f"bulk_unfollow_non_followers user {target_user_id}",
                        auto_wait=auto_wait_on_rate_limit,
                    )

                    if waited and retry_count < max_rate_limit_retries:
                        retry_count += 1
                        print(f"[RETRY] Retrying non-follower @{username} after rate-limit wait...")
                        continue

                    log_result(
                        csv_writer,
                        target_user_id,
                        username,
                        name,
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


def run_bulk_unfollow_non_followers(
    dry_run=DRY_RUN,
    limit=MAX_USERS_TO_PROCESS,
    request_delay_seconds=REQUEST_DELAY_SECONDS,
    stop_on_rate_limit=STOP_ON_RATE_LIMIT,
    auto_wait_on_rate_limit=AUTO_WAIT_ON_RATE_LIMIT,
    max_rate_limit_retries=MAX_RATE_LIMIT_RETRIES,
):
    """Preview or unfollow saved non-follower candidates with resume support."""
    print("Loading access token...")
    access_token = load_access_token()

    print("Verifying authenticated user...")
    live_profile = get_profile(access_token)
    source_user_id = live_profile["id"]

    print("\nAuthenticated as:")
    print(f"Name: {live_profile['name']}")
    print(f"Username: @{live_profile['username']}")
    print(f"User ID: {source_user_id}")

    print("\nLoading non-follower candidates file...")
    file_user, summary, original_candidates = load_candidates_file()

    print("\nCandidate file created for:")
    print(f"Name: {file_user.get('name')}")
    print(f"Username: @{file_user.get('username')}")
    print(f"User ID: {file_user.get('id')}")

    if str(file_user.get("id")) != str(source_user_id):
        raise ValueError(
            "Candidate file user ID does not match the currently authenticated user."
        )

    print("\nChecking prior logs for resume support...")
    processed_ids = get_successfully_processed_user_ids()
    remaining_candidates, skipped_count = filter_out_already_processed_candidates(
        original_candidates,
        processed_ids,
    )

    users_to_process = preview_candidates(
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

    success_count, failure_count, stopped_due_to_rate_limit = process_unfollows(
        access_token,
        source_user_id,
        users_to_process,
        log_file_path,
        dry_run=dry_run,
        request_delay_seconds=request_delay_seconds,
        stop_on_rate_limit=stop_on_rate_limit,
        auto_wait_on_rate_limit=auto_wait_on_rate_limit,
        max_rate_limit_retries=max_rate_limit_retries,
    )

    print("\n--- NON-FOLLOWER UNFOLLOW SUMMARY ---")
    if dry_run:
        print("Mode: DRY RUN")
        print(f"Previewed {len(users_to_process)} non-follower candidates.")
        print("No changes were made.")
    else:
        print("Mode: LIVE")
        print(f"Successfully unfollowed: {success_count}")
        print(f"Failed to unfollow: {failure_count}")

        if stopped_due_to_rate_limit:
            print("Run stopped early because of rate limiting.")
            print("You can rerun later and resume from the remaining candidates.")

    print(f"Log saved to: {log_file_path}")

    return {
        "profile": live_profile,
        "original_candidates_count": len(original_candidates),
        "remaining_candidates_count": len(remaining_candidates),
        "users_selected_count": len(users_to_process),
        "skipped_count": skipped_count,
        "dry_run": dry_run,
        "success_count": success_count,
        "failure_count": failure_count,
        "stopped_due_to_rate_limit": stopped_due_to_rate_limit,
        "log_file_path": log_file_path,
    }


def main():
    run_bulk_unfollow_non_followers()


if __name__ == "__main__":
    main()
