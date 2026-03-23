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


def preview_likes_to_unlike(likes):
    print("\n--- DRY RUN: Likes Preview ---")
    print(f"Would unlike {len(likes)} liked tweets from this page.")

    if not likes:
        print("No liked tweets found.")
        return

    print("\nSample liked tweets that would be unliked:")
    for tweet in likes[:MAX_LIKES_PREVIEW]:
        tweet_id = tweet.get("id", "unknown_id")
        tweet_text = tweet.get("text", "").replace("\n", " ").strip()
        print(f"- [{tweet_id}] {tweet_text[:100]}")


def preview_following_to_unfollow(following):
    print("\n--- DRY RUN: Following Preview ---")
    print(f"Would unfollow {len(following)} accounts from this page.")

    if not following:
        print("No followed accounts found.")
        return

    print("\nSample accounts that would be unfollowed:")
    for user in following[:MAX_FOLLOWING_PREVIEW]:
        user_id = user.get("id", "unknown_id")
        username = user.get("username", "unknown_username")
        name = user.get("name", "unknown_name")
        print(f"- [{user_id}] @{username} ({name})")


def main():
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

    preview_likes_to_unlike(likes)
    preview_following_to_unfollow(following)

    print("\nDry run complete.")
    print("No changes were made to your account.")


if __name__ == "__main__":
    main()
