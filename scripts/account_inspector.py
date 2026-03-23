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


def main():
    print("Loading access token...")
    access_token = load_access_token()

    print("Fetching authenticated user profile...")
    profile = get_profile(access_token)
    user_id = profile["id"]

    print("\nProfile:")
    print(f"Name: {profile['name']}")
    print(f"Username: @{profile['username']}")
    print(f"User ID: {user_id}")

    print("\nFetching liked tweets...")
    likes = get_likes(access_token, user_id)
    print(f"Found {len(likes)} liked tweets")

    for tweet in likes[:5]:
        print(f"- {tweet.get('text', '')[:80]}")

    print("\nFetching following list...")
    following = get_following(access_token, user_id)
    print(f"Following {len(following)} accounts")

    for user in following[:5]:
        print(f"- @{user.get('username', 'unknown')}")

    print("\nInspection complete.")


if __name__ == "__main__":
    main()
