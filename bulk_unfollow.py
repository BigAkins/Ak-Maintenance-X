import csv
import json
import os
import time
from datetime import datetime

import requests

TOKEN_FILE = "token.json"
ME_URL = "https://api.x.com/2/users/me"
FOLLOWING_URL = "https://api.x.com/2/users/{user_id}/following"
UNFOLLOW_URL = "https://api.x.com/2/users/{source_user_id}/following/{target_user_id}"

DRY_RUN = True
REQUEST_DELAY_SECONDS = 1.0
MAX_USERS_TO_PROCESS = 5

# Accounts you never want to unfollow
KEEP_USERNAMES = {
    "akinooola",
}

LOGS_DIR = "logs"


def load_access_token():
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as file:
            token_data = json.load(file)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            "token.json not found. Run auth_test.py first to authenticate."
        ) from exc

    access_token = token_data.get("access_token")
    if not access_token:
        raise ValueError("No access_token found in token.json")

    return access_token


def make_headers(access_token):
    return {
        "Authorization": f"Bearer {access_token}",
    }


def get_profile(access_token):
    response = requests.get(
        ME_URL,
        headers=make_headers(access_token),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["data"]


def get_following(access_token, user_id):
    url = FOLLOWING_URL.format(user_id=user_id)

    response = requests.get(
        url,
        headers=make_headers(access_token),
        timeout=30,
        params={"max_results": 100},
    )
    response.raise_for_status()

    data = response.json()
    return data.get("data", [])


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
    return response.json()


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


def is_protected_user(user):
    username = user.get("username", "")
    return username in KEEP_USERNAMES


def filter_unfollow_candidates(users):
    protected_users = []
    unfollow_candidates = []

    for user in users:
        if is_protected_user(user):
            protected_users.append(user)
        else:
            unfollow_candidates.append(user)

    return protected_users, unfollow_candidates


def preview_users(all_users, protected_users, unfollow_candidates):
    print("\n--- BULK UNFOLLOW PREVIEW ---")
    print(f"Found {len(all_users)} followed accounts on this page.")
    print(f"Protected accounts found: {len(protected_users)}")
    print(f"Eligible unfollow candidates found: {len(unfollow_candidates)}")
    print(f"Configured to process up to {MAX_USERS_TO_PROCESS} accounts.")

    users_to_process = unfollow_candidates[:MAX_USERS_TO_PROCESS]

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

    if DRY_RUN:
        print("\nDRY_RUN is ON. No accounts will actually be unfollowed.")

    return users_to_process


def process_unfollows(access_token, source_user_id, users_to_process, log_file_path):
    success_count = 0
    failure_count = 0

    with open(log_file_path, "w", newline="", encoding="utf-8") as log_file:
        csv_writer = csv.writer(log_file)
        write_log_header(csv_writer)

        for user in users_to_process:
            target_user_id = user.get("id", "unknown_id")
            username = user.get("username", "unknown_username")
            name = user.get("name", "unknown_name")

            if DRY_RUN:
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

            try:
                result = unfollow_user(access_token, source_user_id, target_user_id)
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
            except requests.HTTPError as error:
                print(f"[FAILED] Could not unfollow @{username} ({target_user_id}): {error}")
                log_result(
                    csv_writer,
                    target_user_id,
                    username,
                    name,
                    "FAILED",
                    str(error),
                )
                failure_count += 1

            time.sleep(REQUEST_DELAY_SECONDS)

    return success_count, failure_count


def main():
    print("Loading access token...")
    access_token = load_access_token()

    print("Fetching authenticated user profile...")
    profile = get_profile(access_token)
    source_user_id = profile["id"]

    print("\nAuthenticated as:")
    print(f"Name: {profile['name']}")
    print(f"Username: @{profile['username']}")
    print(f"User ID: {source_user_id}")

    print("\nFetching following list...")
    following = get_following(access_token, source_user_id)

    protected_users, unfollow_candidates = filter_unfollow_candidates(following)

    users_to_process = preview_users(
        following,
        protected_users,
        unfollow_candidates,
    )

    ensure_logs_dir()
    log_file_path = build_log_file_path()

    print(f"\nLog file will be written to: {log_file_path}")

    success_count, failure_count = process_unfollows(
        access_token,
        source_user_id,
        users_to_process,
        log_file_path,
    )

    print("\n--- BULK UNFOLLOW SUMMARY ---")
    if DRY_RUN:
        print("Mode: DRY RUN")
        print(f"Previewed {len(users_to_process)} eligible accounts.")
        print("No changes were made.")
    else:
        print("Mode: LIVE")
        print(f"Successfully unfollowed: {success_count}")
        print(f"Failed to unfollow: {failure_count}")

    print(f"Log saved to: {log_file_path}")


if __name__ == "__main__":
    main()