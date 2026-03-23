import json

try:
    from scripts._bootstrap import bootstrap_project_root
except ModuleNotFoundError:
    from _bootstrap import bootstrap_project_root

bootstrap_project_root()

from ak_maintenance_x.cleanup_config import (
    POST_DELETE_CANDIDATES_FILE,
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
START_TIME = "2026-03-31T00:00:00Z"
END_TIME = "2026-04-03T00:00:00Z"


def get_posts_in_date_range(access_token, user_id, start_time=None, end_time=None):
    url = USER_TWEETS_URL.format(user_id=user_id)

    posts, includes = fetch_all_timeline_posts(
        access_token=access_token,
        base_url=url,
        max_results_per_page=TIMELINE_MAX_RESULTS_PER_PAGE,
        start_time=start_time,
        end_time=end_time,
        exclude=["retweets"],
        tweet_fields=["created_at"],
        expansions=None,
    )

    return posts, includes


def build_post_delete_candidates(posts):
    candidates = []

    for post in posts:
        candidates.append(
            {
                "id": post.get("id"),
                "created_at": post.get("created_at"),
                "text": post.get("text", ""),
            }
        )

    return candidates


def preview_post_candidates(candidates):
    print("\n--- POST DELETE ANALYSIS PREVIEW ---")
    print(f"Eligible post-delete candidates found: {len(candidates)}")

    if not candidates:
        print("\nNo posts found in the selected date range.")
        return

    print("\nSample post-delete candidates:")
    for post in candidates[:10]:
        print(
            f"- tweet_id={post.get('id')} | "
            f"created_at={post.get('created_at')} | "
            f"text={post.get('text', '')[:80]}"
        )


def save_post_candidates(profile, posts, candidates, start_time, end_time):
    output_data = {
        "authenticated_user": {
            "id": profile.get("id"),
            "name": profile.get("name"),
            "username": profile.get("username"),
        },
        "summary": {
            "timeline_posts_found": len(posts),
            "post_delete_candidates_found": len(candidates),
            "start_time": start_time,
            "end_time": end_time,
            "note": "Filtered from the authenticated user's own timeline within the provided date range.",
        },
        "post_delete_candidates": candidates,
    }

    with open(POST_DELETE_CANDIDATES_FILE, "w", encoding="utf-8") as file:
        json.dump(output_data, file, indent=2)

    print(f"\nSaved post-delete candidate file to: {POST_DELETE_CANDIDATES_FILE}")


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
    print("\nNote: retweets are excluded from this post-delete analysis.")

    print("\nFetching timeline posts in date range...")
    posts, _includes = get_posts_in_date_range(
        access_token,
        user_id,
        start_time=START_TIME,
        end_time=END_TIME,
    )

    print("\nBuilding post-delete candidates...")
    candidates = build_post_delete_candidates(posts)

    preview_post_candidates(candidates)

    save_post_candidates(
        profile,
        posts,
        candidates,
        START_TIME,
        END_TIME,
    )

    print("\nAnalysis complete.")
    print("No account changes were made.")


if __name__ == "__main__":
    main()
