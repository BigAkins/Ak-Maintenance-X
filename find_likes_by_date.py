import json
from datetime import datetime, timezone

import requests

from cleanup_config import (
    LIKE_CANDIDATES_FILE,
    LIKED_TWEETS_MAX_RESULTS_PER_PAGE,
)
from cleanup_helpers import (
    load_access_token,
    get_profile,
    make_headers,
)

LIKED_TWEETS_URL = "https://api.x.com/2/users/{user_id}/liked_tweets"

# Example date window:
# March 31 through April 2 (inclusive) in UTC-style API format
START_TIME = "2026-03-31T00:00:00Z"
END_TIME = "2026-04-03T00:00:00Z"


def parse_x_datetime(date_string):
    return datetime.fromisoformat(date_string.replace("Z", "+00:00"))


def is_in_date_range(created_at, start_time, end_time):
    created_dt = parse_x_datetime(created_at)
    start_dt = parse_x_datetime(start_time)
    end_dt = parse_x_datetime(end_time)

    return start_dt <= created_dt < end_dt


def fetch_all_liked_tweets(access_token, user_id):
    url = LIKED_TWEETS_URL.format(user_id=user_id)

    all_tweets = []
    next_token = None
    page_number = 1

    while True:
        params = {
            "max_results": LIKED_TWEETS_MAX_RESULTS_PER_PAGE,
            "tweet.fields": "created_at,author_id",
        }

        if next_token:
            params["pagination_token"] = next_token

        response = requests.get(
            url,
            headers=make_headers(access_token),
            params=params,
            timeout=30,
        )
        response.raise_for_status()

        payload = response.json()
        page_tweets = payload.get("data", [])
        meta = payload.get("meta", {})

        all_tweets.extend(page_tweets)

        print(
            f"Fetched liked-tweets page {page_number}: "
            f"{len(page_tweets)} tweets "
            f"(total so far: {len(all_tweets)})"
        )

        next_token = meta.get("next_token")
        if not next_token:
            break

        page_number += 1

    return all_tweets


def get_like_candidates_by_post_date(liked_tweets, start_time, end_time):
    candidates = []

    for tweet in liked_tweets:
        created_at = tweet.get("created_at")
        if not created_at:
            continue

        if is_in_date_range(created_at, start_time, end_time):
            candidates.append(
                {
                    "id": tweet.get("id"),
                    "created_at": created_at,
                    "author_id": tweet.get("author_id"),
                    "text": tweet.get("text", ""),
                }
            )

    return candidates


def preview_like_candidates(candidates):
    print("\n--- LIKE ANALYSIS PREVIEW ---")
    print(f"Eligible like candidates found: {len(candidates)}")

    if not candidates:
        print("\nNo liked posts found in the selected date range.")
        return

    print("\nSample like candidates:")
    for tweet in candidates[:10]:
        print(
            f"- tweet_id={tweet.get('id')} | "
            f"created_at={tweet.get('created_at')} | "
            f"text={tweet.get('text', '')[:80]}"
        )


def save_like_candidates(profile, liked_tweets, candidates, start_time, end_time):
    output_data = {
        "authenticated_user": {
            "id": profile.get("id"),
            "name": profile.get("name"),
            "username": profile.get("username"),
        },
        "summary": {
            "liked_tweets_found_total": len(liked_tweets),
            "like_candidates_found": len(candidates),
            "start_time": start_time,
            "end_time": end_time,
            "note": "Filtered by liked post created_at, not by the time the like action happened.",
        },
        "like_candidates": candidates,
    }

    with open(LIKE_CANDIDATES_FILE, "w", encoding="utf-8") as file:
        json.dump(output_data, file, indent=2)

    print(f"\nSaved like candidate file to: {LIKE_CANDIDATES_FILE}")


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

    print("\nUsing date range:")
    print(f"START_TIME: {START_TIME}")
    print(f"END_TIME:   {END_TIME}")
    print("\nNote: filtering is based on the liked post's created_at date.")

    print("\nFetching all liked tweets...")
    liked_tweets = fetch_all_liked_tweets(access_token, user_id)

    print("\nFiltering liked tweets by created_at date range...")
    candidates = get_like_candidates_by_post_date(
        liked_tweets,
        START_TIME,
        END_TIME,
    )

    preview_like_candidates(candidates)

    save_like_candidates(
        profile,
        liked_tweets,
        candidates,
        START_TIME,
        END_TIME,
    )

    print("\nAnalysis complete.")
    print("No account changes were made.")


if __name__ == "__main__":
    main()