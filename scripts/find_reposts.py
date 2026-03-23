import json

try:
    from scripts._bootstrap import bootstrap_project_root
except ModuleNotFoundError:
    from _bootstrap import bootstrap_project_root

bootstrap_project_root()

from ak_maintenance_x.cleanup_config import (
    REPOST_CANDIDATES_FILE,
    TIMELINE_MAX_RESULTS_PER_PAGE,
)
from ak_maintenance_x.cleanup_helpers import (
    load_access_token,
    get_profile,
    fetch_all_timeline_posts,
)

USER_TWEETS_URL = "https://api.x.com/2/users/{user_id}/tweets"

# Example date window:
# March 31 through April 2 (inclusive) in UTC-style API format
START_TIME = "2018-01-01T00:00:00Z"
END_TIME = "2020-12-30T00:00:00Z"


def get_timeline_posts(access_token, user_id, start_time=None, end_time=None):
    url = USER_TWEETS_URL.format(user_id=user_id)

    posts, includes = fetch_all_timeline_posts(
        access_token=access_token,
        base_url=url,
        max_results_per_page=TIMELINE_MAX_RESULTS_PER_PAGE,
        start_time=start_time,
        end_time=end_time,
        exclude=None,
        tweet_fields=["created_at", "referenced_tweets"],
        expansions=None,
    )

    return posts, includes


def get_repost_candidates(posts):
    repost_candidates = []

    for post in posts:
        referenced_tweets = post.get("referenced_tweets", [])

        for referenced in referenced_tweets:
            if referenced.get("type") == "retweeted":
                repost_candidates.append(
                    {
                        "id": post.get("id"),
                        "created_at": post.get("created_at"),
                        "referenced_tweet_id": referenced.get("id"),
                        "text": post.get("text", ""),
                    }
                )
                break

    return repost_candidates


def preview_reposts(repost_candidates):
    print("\n--- REPOST ANALYSIS PREVIEW ---")
    print(f"Eligible repost candidates found: {len(repost_candidates)}")

    if not repost_candidates:
        print("\nNo repost candidates found in the selected date range.")
        return

    print("\nSample repost candidates:")
    for repost in repost_candidates[:10]:
        print(
            f"- repost_id={repost.get('id')} | "
            f"referenced_tweet_id={repost.get('referenced_tweet_id')} | "
            f"created_at={repost.get('created_at')}"
        )


def save_repost_candidates(profile, posts, repost_candidates, start_time, end_time):
    output_data = {
        "authenticated_user": {
            "id": profile.get("id"),
            "name": profile.get("name"),
            "username": profile.get("username"),
        },
        "summary": {
            "timeline_posts_found": len(posts),
            "repost_candidates_found": len(repost_candidates),
            "start_time": start_time,
            "end_time": end_time,
        },
        "repost_candidates": repost_candidates,
    }

    with open(REPOST_CANDIDATES_FILE, "w", encoding="utf-8") as file:
        json.dump(output_data, file, indent=2)

    print(f"\nSaved repost candidate file to: {REPOST_CANDIDATES_FILE}")


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

    print("\nFetching timeline posts in date range...")
    posts, _includes = get_timeline_posts(
        access_token,
        user_id,
        start_time=START_TIME,
        end_time=END_TIME,
    )

    print("\nFinding repost candidates...")
    repost_candidates = get_repost_candidates(posts)

    preview_reposts(repost_candidates)

    save_repost_candidates(
        profile,
        posts,
        repost_candidates,
        START_TIME,
        END_TIME,
    )

    print("\nAnalysis complete.")
    print("No account changes were made.")


if __name__ == "__main__":
    main()
