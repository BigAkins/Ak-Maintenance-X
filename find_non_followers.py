import json
import os

import requests

from cleanup_config import (
    TOKEN_FILE,
    PROTECTED_ACCOUNTS_FILE,
    NON_FOLLOWER_CANDIDATES_FILE,
    MAX_RESULTS_PER_PAGE,
    DEFAULT_KEEP_USERNAMES,
    DEFAULT_KEEP_USER_IDS,
)

ME_URL = "https://api.x.com/2/users/me"
FOLLOWING_URL = "https://api.x.com/2/users/{user_id}/following"
FOLLOWERS_URL = "https://api.x.com/2/users/{user_id}/followers"


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


def normalize_username(username):
    return username.strip().lower().lstrip("@")


def load_protected_accounts():
    keep_usernames = {normalize_username(name) for name in DEFAULT_KEEP_USERNAMES}
    keep_user_ids = {str(user_id).strip() for user_id in DEFAULT_KEEP_USER_IDS}

    if not os.path.exists(PROTECTED_ACCOUNTS_FILE):
        print(
            f"[INFO] {PROTECTED_ACCOUNTS_FILE} not found. "
            "Using default built-in protected accounts only."
        )
        return keep_usernames, keep_user_ids

    try:
        with open(PROTECTED_ACCOUNTS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        file_usernames = data.get("keep_usernames", [])
        file_user_ids = data.get("keep_user_ids", [])

        keep_usernames.update(normalize_username(name) for name in file_usernames)
        keep_user_ids.update(str(user_id).strip() for user_id in file_user_ids)

        print(f"[INFO] Loaded protected accounts from {PROTECTED_ACCOUNTS_FILE}")
        return keep_usernames, keep_user_ids

    except Exception as error:
        print(
            f"[WARNING] Could not read {PROTECTED_ACCOUNTS_FILE}: {error}. "
            "Using default built-in protected accounts only."
        )
        return keep_usernames, keep_user_ids


def is_protected_user(user, keep_usernames, keep_user_ids):
    user_id = str(user.get("id", "")).strip()
    username = normalize_username(user.get("username", ""))

    return user_id in keep_user_ids or username in keep_usernames


def fetch_all_users_from_paginated_endpoint(access_token, base_url):
    all_users = []
    next_token = None
    page_number = 1

    while True:
        params = {
            "max_results": MAX_RESULTS_PER_PAGE,
        }

        if next_token:
            params["pagination_token"] = next_token

        response = requests.get(
            base_url,
            headers=make_headers(access_token),
            params=params,
            timeout=30,
        )
        response.raise_for_status()

        payload = response.json()
        page_users = payload.get("data", [])
        meta = payload.get("meta", {})

        all_users.extend(page_users)

        print(
            f"Fetched page {page_number}: "
            f"{len(page_users)} users "
            f"(total so far: {len(all_users)})"
        )

        next_token = meta.get("next_token")
        if not next_token:
            break

        page_number += 1

    return all_users


def get_all_following(access_token, user_id):
    url = FOLLOWING_URL.format(user_id=user_id)
    return fetch_all_users_from_paginated_endpoint(access_token, url)


def get_all_followers(access_token, user_id):
    url = FOLLOWERS_URL.format(user_id=user_id)
    return fetch_all_users_from_paginated_endpoint(access_token, url)


def get_non_followers(following, followers):
    follower_ids = {str(user.get("id", "")).strip() for user in followers}
    non_followers = []

    for user in following:
        followed_user_id = str(user.get("id", "")).strip()
        if followed_user_id and followed_user_id not in follower_ids:
            non_followers.append(user)

    return non_followers


def split_protected_and_candidates(users, keep_usernames, keep_user_ids):
    protected_users = []
    candidates = []

    for user in users:
        if is_protected_user(user, keep_usernames, keep_user_ids):
            protected_users.append(user)
        else:
            candidates.append(user)

    return protected_users, candidates


def save_candidates(
    profile,
    following,
    followers,
    non_followers,
    protected_users,
    candidates,
):
    output_data = {
        "authenticated_user": {
            "id": profile.get("id"),
            "name": profile.get("name"),
            "username": profile.get("username"),
        },
        "summary": {
            "following_count_total": len(following),
            "followers_count_total": len(followers),
            "non_followers_found": len(non_followers),
            "protected_non_followers_skipped": len(protected_users),
            "eligible_candidates": len(candidates),
        },
        "protected_users": protected_users,
        "eligible_candidates": candidates,
    }

    with open(NON_FOLLOWER_CANDIDATES_FILE, "w", encoding="utf-8") as file:
        json.dump(output_data, file, indent=2)

    print(f"\nSaved candidate file to: {NON_FOLLOWER_CANDIDATES_FILE}")


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

    print("\nFetching all following pages...")
    following = get_all_following(access_token, user_id)

    print("\nFetching all followers pages...")
    followers = get_all_followers(access_token, user_id)

    print("\nLoading protected accounts...")
    keep_usernames, keep_user_ids = load_protected_accounts()

    print("\nComparing full following vs full followers...")
    non_followers = get_non_followers(following, followers)

    print("Applying protected keep list...")
    protected_users, candidates = split_protected_and_candidates(
        non_followers,
        keep_usernames,
        keep_user_ids,
    )

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