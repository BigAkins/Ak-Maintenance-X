import json

try:
    from scripts._bootstrap import bootstrap_project_root
except ModuleNotFoundError:
    from _bootstrap import bootstrap_project_root

bootstrap_project_root()

from ak_maintenance_x.cleanup_config import (
    NON_FOLLOWER_CANDIDATES_FILE,
    MAX_RESULTS_PER_PAGE,
)
from ak_maintenance_x.cleanup_helpers import (
    load_access_token,
    get_profile,
    load_protected_accounts,
    normalize_username,
    fetch_all_users_from_paginated_endpoint,
)

FOLLOWING_URL = "https://api.x.com/2/users/{user_id}/following"
FOLLOWERS_URL = "https://api.x.com/2/users/{user_id}/followers"


def is_protected_user(user, keep_usernames, keep_user_ids):
    user_id = str(user.get("id", "")).strip()
    username = normalize_username(user.get("username", ""))

    return user_id in keep_user_ids or username in keep_usernames


def get_all_following(access_token, user_id):
    url = FOLLOWING_URL.format(user_id=user_id)
    return fetch_all_users_from_paginated_endpoint(
        access_token,
        url,
        MAX_RESULTS_PER_PAGE,
    )


def get_all_followers(access_token, user_id):
    url = FOLLOWERS_URL.format(user_id=user_id)
    return fetch_all_users_from_paginated_endpoint(
        access_token,
        url,
        MAX_RESULTS_PER_PAGE,
    )


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
