import json
import os

import requests

TOKEN_FILE = "token.json"
OUTPUT_FILE = "non_follower_candidates.json"

ME_URL = "https://api.x.com/2/users/me"
FOLLOWING_URL = "https://api.x.com/2/users/{user_id}/following"
FOLLOWERS_URL = "https://api.x.com/2/users/{user_id}/followers"

KEEP_USERNAMES = {
    "Akinooola",
}

KEEP_USER_IDS = {
    # Add exact protected IDs here if you want
    # "1509718054346788866",
}


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


def get_followers(access_token, user_id):
    url = FOLLOWERS_URL.format(user_id=user_id)

    response = requests.get(
        url,
        headers=make_headers(access_token),
        timeout=30,
        params={"max_results": 100},
    )
    response.raise_for_status()

    data = response.json()
    return data.get("data", [])


def normalize_username(username):
    return username.strip().lower().lstrip("@")


def is_protected_user(user):
    user_id = str(user.get("id", "")).strip()
    username = normalize_username(user.get("username", ""))

    return user_id in KEEP_USER_IDS or username in KEEP_USERNAMES


def get_non_followers(following, followers):
    follower_ids = {str(user.get("id", "")).strip() for user in followers}
    non_followers = []

    for user in following:
        followed_user_id = str(user.get("id", "")).strip()
        if followed_user_id and followed_user_id not in follower_ids:
            non_followers.append(user)

    return non_followers


def split_protected_and_candidates(users):
    protected_users = []
    candidates = []

    for user in users:
        if is_protected_user(user):
            protected_users.append(user)
        else:
            candidates.append(user)

    return protected_users, candidates


def save_candidates(profile, following, followers, non_followers, protected_users, candidates):
    output_data = {
        "authenticated_user": {
            "id": profile.get("id"),
            "name": profile.get("name"),
            "username": profile.get("username"),
        },
        "summary": {
            "following_count_on_page": len(following),
            "followers_count_on_page": len(followers),
            "non_followers_found": len(non_followers),
            "protected_non_followers_skipped": len(protected_users),
            "eligible_candidates": len(candidates),
        },
        "protected_users": protected_users,
        "eligible_candidates": candidates,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(output_data, file, indent=2)

    print(f"\nSaved candidate file to: {OUTPUT_FILE}")


def preview_results(protected_users, candidates):
    print("\n--- NON-FOLLOWER ANALYSIS PREVIEW ---")
    print(f"Protected non-followers skipped: {len(protected_users)}")
    print(f"Eligible non-follower candidates: {len(candidates)}")

    if protected_users:
        print("\nProtected users skipped:")
        for user in protected_users[:10]:
            print(
                f"- [{user.get('id')}] "
                f"@{user.get('username')} "
                f"({user.get('name')})"
            )

    if candidates:
        print("\nEligible non-follower candidates:")
        for user in candidates[:10]:
            print(
                f"- [{user.get('id')}] "
                f"@{user.get('username')} "
                f"({user.get('name')})"
            )
    else:
        print("\nNo eligible non-follower candidates found.")


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

    print("\nFetching following list...")
    following = get_following(access_token, user_id)

    print("Fetching followers list...")
    followers = get_followers(access_token, user_id)

    print("\nComparing following vs followers...")
    non_followers = get_non_followers(following, followers)

    print("Applying protected keep list...")
    protected_users, candidates = split_protected_and_candidates(non_followers)

    preview_results(protected_users, candidates)

    save_candidates(
        profile,
        following,
        followers,
        non_followers,
        protected_users,
        candidates,
    )

    print("\nAnalysis complete.")
    print("No account changes were made.")


if __name__ == "__main__":
    main()