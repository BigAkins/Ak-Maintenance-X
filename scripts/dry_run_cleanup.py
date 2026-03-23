import requests

try:
    from scripts._bootstrap import bootstrap_project_root
except ModuleNotFoundError:
    from _bootstrap import bootstrap_project_root

bootstrap_project_root()

from ak_maintenance_x.cleanup_helpers import (
    load_access_token,
    get_profile,
    make_headers,
)

LIKES_URL = "https://api.x.com/2/users/{user_id}/liked_tweets"
FOLLOWING_URL = "https://api.x.com/2/users/{user_id}/following"

MAX_LIKES_PREVIEW = 10
MAX_FOLLOWING_PREVIEW = 10


def get_likes(access_token, user_id):
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


def preview_likes_to_unlike(likes, max_likes_preview=MAX_LIKES_PREVIEW):
    print("\n--- DRY RUN: Likes Preview ---")
    print(f"Would unlike {len(likes)} liked tweets from this page.")

    if not likes:
        print("No liked tweets found.")
        return

    print("\nSample liked tweets that would be unliked:")
    for tweet in likes[:max_likes_preview]:
        tweet_id = tweet.get("id", "unknown_id")
        tweet_text = tweet.get("text", "").replace("\n", " ").strip()
        print(f"- [{tweet_id}] {tweet_text[:100]}")


def preview_following_to_unfollow(
    following,
    max_following_preview=MAX_FOLLOWING_PREVIEW,
):
    print("\n--- DRY RUN: Following Preview ---")
    print(f"Would unfollow {len(following)} accounts from this page.")

    if not following:
        print("No followed accounts found.")
        return

    print("\nSample accounts that would be unfollowed:")
    for user in following[:max_following_preview]:
        user_id = user.get("id", "unknown_id")
        username = user.get("username", "unknown_username")
        name = user.get("name", "unknown_name")
        print(f"- [{user_id}] @{username} ({name})")


def run_dry_run_cleanup(
    max_likes_preview=MAX_LIKES_PREVIEW,
    max_following_preview=MAX_FOLLOWING_PREVIEW,
):
    """Preview cleanup targets and return a dry-run summary dict."""
    print("Loading access token...")
    access_token = load_access_token()

    print("Fetching profile...")
    profile = get_profile(access_token)
    user_id = profile["id"]

    print("\nAuthenticated as:")
    print(f"Name: {profile['name']}")
    print(f"Username: @{profile['username']}")
    print(f"User ID: {user_id}")

    print("\nFetching liked tweets for dry run...")
    likes = get_likes(access_token, user_id)

    print("Fetching following list for dry run...")
    following = get_following(access_token, user_id)

    preview_likes_to_unlike(likes, max_likes_preview=max_likes_preview)
    preview_following_to_unfollow(
        following,
        max_following_preview=max_following_preview,
    )

    print("\nDry run complete.")
    print("No changes were made to your account.")

    summary = {
        "liked_tweets_found": len(likes),
        "following_found": len(following),
        "likes_previewed": min(len(likes), max_likes_preview),
        "following_previewed": min(len(following), max_following_preview),
    }

    return {
        "profile": profile,
        "mode": "DRY RUN",
        "summary": summary,
    }


def main():
    run_dry_run_cleanup()


if __name__ == "__main__":
    main()
