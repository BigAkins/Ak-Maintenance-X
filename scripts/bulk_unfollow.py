import csv
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
    DRY_RUN_DEFAULT,
    REQUEST_DELAY_SECONDS_DEFAULT,
    MAX_USERS_TO_PROCESS_DEFAULT,
    MAX_RESULTS_PER_PAGE,
    STOP_ON_RATE_LIMIT_DEFAULT,
    AUTO_WAIT_ON_RATE_LIMIT_DEFAULT,
    MAX_RATE_LIMIT_RETRIES_DEFAULT,
)
from ak_maintenance_x.cleanup_helpers import (
    load_access_token,
    get_profile,
    load_protected_accounts,
    normalize_username,
    make_headers,
    fetch_all_users_from_paginated_endpoint,
)
from ak_maintenance_x.cleanup_rate_limits import (
    maybe_wait_from_success_response,
    handle_rate_limit_http_error,
)

FOLLOWING_URL = "https://api.x.com/2/users/{user_id}/following"
UNFOLLOW_URL = "https://api.x.com/2/users/{source_user_id}/following/{target_user_id}"

DRY_RUN = DRY_RUN_DEFAULT
REQUEST_DELAY_SECONDS = REQUEST_DELAY_SECONDS_DEFAULT
MAX_USERS_TO_PROCESS = MAX_USERS_TO_PROCESS_DEFAULT
STOP_ON_RATE_LIMIT = STOP_ON_RATE_LIMIT_DEFAULT
AUTO_WAIT_ON_RATE_LIMIT = AUTO_WAIT_ON_RATE_LIMIT_DEFAULT
MAX_RATE_LIMIT_RETRIES = MAX_RATE_LIMIT_RETRIES_DEFAULT


def get_all_following(access_token, user_id):
    url = FOLLOWING_URL.format(user_id=user_id)
    return fetch_all_users_from_paginated_endpoint(
        access_token,
        url,
        MAX_RESULTS_PER_PAGE,
    )


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
    return os.path.join(LOGS_DIR, f"bulk_unfollow_log_{timestamp}.csv")


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


def is_protected_user(user, keep_usernames, keep_user_ids):
    user_id = str(user.get("id", "")).strip()
    username = normalize_username(user.get("username", ""))
    return user_id in keep_user_ids or username in keep_usernames


def filter_unfollow_candidates(users, keep_usernames, keep_user_ids):
    protected_users = []
    unfollow_candidates = []

    for user in users:
        if is_protected_user(user, keep_usernames, keep_user_ids):
            protected_users.append(user)
        else:
            unfollow_candidates.append(user)

    return protected_users, unfollow_candidates


def preview_users(
    all_users,
    protected_users,
    unfollow_candidates,
    limit=MAX_USERS_TO_PROCESS,
    dry_run=DRY_RUN,
):
    print("\n--- BULK UNFOLLOW PREVIEW ---")
    print(f"Found {len(all_users)} followed accounts total.")
    print(f"Protected accounts found: {len(protected_users)}")
    print(f"Eligible unfollow candidates found: {len(unfollow_candidates)}")
    print(f"Configured to process up to {limit} accounts.")

    users_to_process = unfollow_candidates[:limit]

    if protected_users:
        print("\nProtected accounts that will be skipped:")
        for user in protected_users[:10]:
            user_id = user.get("id", "unknown_id")
            username = user.get("username", "unknown_username")
            name = user.get("name", "unknown_name")
            print(f"- [{user_id}] @{username} ({name})")

    if not users_to_process:
        print("\nNo eligible accounts found to process.")
        return users_to_process

    print("\nAccounts that would be processed:")
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
                print(f"[DRY RUN] Would unfollow @{username} ({target_user_id})")
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

                    print(f"[SUCCESS] Unfollowed @{username} ({target_user_id}): {result}")
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
                        action_label=f"bulk_unfollow user {target_user_id}",
                        auto_wait=auto_wait_on_rate_limit,
                    )
                    break

                except requests.HTTPError as error:
                    print(f"[FAILED] Could not unfollow @{username} ({target_user_id}): {error}")

                    waited = handle_rate_limit_http_error(
                        error,
                        action_label=f"bulk_unfollow user {target_user_id}",
                        auto_wait=auto_wait_on_rate_limit,
                    )

                    if waited and retry_count < max_rate_limit_retries:
                        retry_count += 1
                        print(f"[RETRY] Retrying unfollow for @{username} after rate-limit wait...")
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


def run_bulk_unfollow(
    dry_run=DRY_RUN,
    limit=MAX_USERS_TO_PROCESS,
    request_delay_seconds=REQUEST_DELAY_SECONDS,
    stop_on_rate_limit=STOP_ON_RATE_LIMIT,
    auto_wait_on_rate_limit=AUTO_WAIT_ON_RATE_LIMIT,
    max_rate_limit_retries=MAX_RATE_LIMIT_RETRIES,
):
    """Preview or unfollow eligible accounts from the current following list."""
    print("Loading access token...")
    access_token = load_access_token()

    print("Fetching authenticated user profile...")
    profile = get_profile(access_token)
    source_user_id = profile["id"]

    print("\nAuthenticated as:")
    print(f"Name: {profile['name']}")
    print(f"Username: @{profile['username']}")
    print(f"User ID: {source_user_id}")

    print("\nFetching all following pages...")
    following = get_all_following(access_token, source_user_id)

    print("Loading protected accounts...")
    keep_usernames, keep_user_ids = load_protected_accounts()

    protected_users, unfollow_candidates = filter_unfollow_candidates(
        following,
        keep_usernames,
        keep_user_ids,
    )

    users_to_process = preview_users(
        following,
        protected_users,
        unfollow_candidates,
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

    print("\n--- BULK UNFOLLOW SUMMARY ---")
    if dry_run:
        print("Mode: DRY RUN")
        print(f"Previewed {len(users_to_process)} eligible accounts.")
        print("No changes were made.")
    else:
        print("Mode: LIVE")
        print(f"Successfully unfollowed: {success_count}")
        print(f"Failed to unfollow: {failure_count}")
        if stopped_due_to_rate_limit:
            print("Run stopped early because of rate limiting.")

    print(f"Log saved to: {log_file_path}")

    return {
        "profile": profile,
        "following_count": len(following),
        "protected_users_count": len(protected_users),
        "unfollow_candidates_count": len(unfollow_candidates),
        "users_selected_count": len(users_to_process),
        "dry_run": dry_run,
        "success_count": success_count,
        "failure_count": failure_count,
        "stopped_due_to_rate_limit": stopped_due_to_rate_limit,
        "log_file_path": log_file_path,
    }


def main():
    run_bulk_unfollow()


if __name__ == "__main__":
    main()
