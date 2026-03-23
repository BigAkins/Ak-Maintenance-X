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

LIKES_URL = "https://api.x.com/2/users/{user_id}/liked_tweets"
UNLIKE_URL = "https://api.x.com/2/users/{user_id}/likes/{tweet_id}"

DRY_RUN = DRY_RUN_DEFAULT
REQUEST_DELAY_SECONDS = REQUEST_DELAY_SECONDS_DEFAULT
MAX_TWEETS_TO_PROCESS = MAX_TWEETS_TO_PROCESS_DEFAULT
STOP_ON_RATE_LIMIT = STOP_ON_RATE_LIMIT_DEFAULT
AUTO_WAIT_ON_RATE_LIMIT = AUTO_WAIT_ON_RATE_LIMIT_DEFAULT
MAX_RATE_LIMIT_RETRIES = MAX_RATE_LIMIT_RETRIES_DEFAULT


def get_liked_tweets(access_token, user_id):
    url = LIKES_URL.format(user_id=user_id)

    response = requests.get(
        url,
        headers=make_headers(access_token),
        timeout=30,
        params={"max_results": 100},
    )
    response.raise_for_status()

    data = response.json()
    return data.get("data", [])


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
    return os.path.join(LOGS_DIR, f"bulk_unlike_log_{timestamp}.csv")


def write_log_header(csv_writer):
    csv_writer.writerow(
        [
            "timestamp",
            "tweet_id",
            "tweet_text_preview",
            "status",
            "details",
        ]
    )


def log_result(csv_writer, tweet_id, tweet_text, status, details):
    csv_writer.writerow(
        [
            datetime.now().isoformat(),
            tweet_id,
            tweet_text[:100].replace("\n", " "),
            status,
            details,
        ]
    )


def preview_tweets(tweets):
    print("\n--- BULK UNLIKE PREVIEW ---")
    print(f"Found {len(tweets)} liked tweets on this page.")
    print(f"Configured to process up to {MAX_TWEETS_TO_PROCESS} tweets.")

    tweets_to_process = tweets[:MAX_TWEETS_TO_PROCESS]

    if not tweets_to_process:
        print("No liked tweets found to process.")
        return tweets_to_process

    print("\nSample tweets to process:")
    for tweet in tweets_to_process[:10]:
        print(f"- [{tweet['id']}] {tweet.get('text', '')[:100]}")

    if DRY_RUN:
        print("\nDRY_RUN is ON. No tweets will actually be unliked.")

    return tweets_to_process


def process_unlikes(access_token, user_id, tweets_to_process, log_file_path):
    success_count = 0
    failure_count = 0
    stopped_due_to_rate_limit = False

    with open(log_file_path, "w", newline="", encoding="utf-8") as log_file:
        csv_writer = csv.writer(log_file)
        write_log_header(csv_writer)

        for tweet in tweets_to_process:
            tweet_id = tweet.get("id", "unknown_id")
            tweet_text = tweet.get("text", "")

            if DRY_RUN:
                print(f"[DRY RUN] Would unlike tweet {tweet_id}")
                log_result(
                    csv_writer,
                    tweet_id,
                    tweet_text,
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
                        tweet_text,
                        "SUCCESS",
                        str(result),
                    )
                    success_count += 1

                    maybe_wait_from_success_response(
                        response,
                        action_label=f"bulk_unlike tweet {tweet_id}",
                        auto_wait=AUTO_WAIT_ON_RATE_LIMIT,
                    )
                    break

                except requests.HTTPError as error:
                    print(f"[FAILED] Could not unlike tweet {tweet_id}: {error}")

                    waited = handle_rate_limit_http_error(
                        error,
                        action_label=f"bulk_unlike tweet {tweet_id}",
                        auto_wait=AUTO_WAIT_ON_RATE_LIMIT,
                    )

                    if waited and retry_count < MAX_RATE_LIMIT_RETRIES:
                        retry_count += 1
                        print(f"[RETRY] Retrying tweet {tweet_id} after rate-limit wait...")
                        continue

                    log_result(
                        csv_writer,
                        tweet_id,
                        tweet_text,
                        "FAILED",
                        str(error),
                    )
                    failure_count += 1

                    if error.response is not None and error.response.status_code == 429:
                        stopped_due_to_rate_limit = True
                        if STOP_ON_RATE_LIMIT:
                            print("\n[STOP] Rate limit persisted. Stopping run early.")
                            return success_count, failure_count, stopped_due_to_rate_limit
                    break

            time.sleep(REQUEST_DELAY_SECONDS)

    return success_count, failure_count, stopped_due_to_rate_limit


def main():
    print("Loading access token...")
    access_token = load_access_token()

    print("Fetching authenticated user profile...")
    profile = get_profile(access_token)
    user_id = profile["id"]

    print("\nAuthenticated as:")
    print(f"Name: {profile['name']}")
    print(f"Username: @{profile['username']}")
    print(f"User ID: {user_id}")

    print("\nFetching liked tweets...")
    liked_tweets = get_liked_tweets(access_token, user_id)

    tweets_to_process = preview_tweets(liked_tweets)

    ensure_logs_dir()
    log_file_path = build_log_file_path()

    print(f"\nLog file will be written to: {log_file_path}")

    success_count, failure_count, stopped_due_to_rate_limit = process_unlikes(
        access_token,
        user_id,
        tweets_to_process,
        log_file_path,
    )

    print("\n--- BULK UNLIKE SUMMARY ---")
    if DRY_RUN:
        print("Mode: DRY RUN")
        print(f"Previewed {len(tweets_to_process)} tweets.")
        print("No changes were made.")
    else:
        print("Mode: LIVE")
        print(f"Successfully unliked: {success_count}")
        print(f"Failed to unlike: {failure_count}")
        if stopped_due_to_rate_limit:
            print("Run stopped early because of rate limiting.")

    print(f"Log saved to: {log_file_path}")


if __name__ == "__main__":
    main()
