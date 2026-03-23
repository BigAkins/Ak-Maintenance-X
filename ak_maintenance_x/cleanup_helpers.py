import json
import os
import time

import requests
from dotenv import load_dotenv

from ak_maintenance_x.cleanup_config import (
    TOKEN_FILE,
    PROTECTED_ACCOUNTS_FILE,
    DEFAULT_KEEP_USERNAMES,
    DEFAULT_KEEP_USER_IDS,
    TOKEN_REFRESH_BUFFER_SECONDS,
    TOKEN_URL,
)

load_dotenv()

ME_URL = "https://api.x.com/2/users/me"
CLIENT_ID = os.getenv("X_CLIENT_ID")


def load_token_data():
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            "token.json not found. Run auth_test.py first to authenticate."
        ) from exc


def save_token_data(token_data):
    with open(TOKEN_FILE, "w", encoding="utf-8") as file:
        json.dump(token_data, file, indent=2)


def token_is_expired_or_near_expiry(token_data):
    expires_at = token_data.get("expires_at")
    expires_in = token_data.get("expires_in")
    obtained_at = token_data.get("obtained_at")

    if expires_at is None:
        if expires_in is None or obtained_at is None:
            return False
        expires_at = obtained_at + expires_in
        token_data["expires_at"] = expires_at
        save_token_data(token_data)

    now = int(time.time())
    return now >= int(expires_at) - TOKEN_REFRESH_BUFFER_SECONDS


def refresh_access_token(token_data):
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        raise ValueError(
            "No refresh_token found in token.json. Re-run auth_test.py with offline.access."
        )

    if not CLIENT_ID:
        raise ValueError("Missing X_CLIENT_ID in environment.")

    data = {
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
    }

    response = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=data,
        timeout=30,
    )
    response.raise_for_status()

    refreshed = response.json()

    now = int(time.time())
    refreshed["obtained_at"] = now

    if "expires_in" in refreshed:
        refreshed["expires_at"] = now + int(refreshed["expires_in"])

    # Preserve refresh token if X does not return a new one
    if "refresh_token" not in refreshed:
        refreshed["refresh_token"] = refresh_token

    save_token_data(refreshed)
    print("[INFO] Access token refreshed successfully.")

    return refreshed


def load_access_token():
    token_data = load_token_data()

    if token_is_expired_or_near_expiry(token_data):
        print("[INFO] Access token expired or near expiry. Refreshing...")
        token_data = refresh_access_token(token_data)

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


def fetch_all_users_from_paginated_endpoint(
    access_token,
    base_url,
    max_results_per_page,
):
    all_users = []
    next_token = None
    page_number = 1

    while True:
        params = {
            "max_results": max_results_per_page,
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


def fetch_all_timeline_posts(
    access_token,
    base_url,
    max_results_per_page,
    start_time=None,
    end_time=None,
    exclude=None,
    tweet_fields=None,
    expansions=None,
):
    all_posts = []
    includes = {}
    next_token = None
    page_number = 1

    while True:
        params = {
            "max_results": max_results_per_page,
        }

        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if exclude:
            params["exclude"] = ",".join(exclude)
        if tweet_fields:
            params["tweet.fields"] = ",".join(tweet_fields)
        if expansions:
            params["expansions"] = ",".join(expansions)
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
        page_posts = payload.get("data", [])
        meta = payload.get("meta", {})

        all_posts.extend(page_posts)

        for key, value in payload.get("includes", {}).items():
            includes.setdefault(key, [])
            includes[key].extend(value)

        print(
            f"Fetched timeline page {page_number}: "
            f"{len(page_posts)} posts "
            f"(total so far: {len(all_posts)})"
        )

        next_token = meta.get("next_token")
        if not next_token:
            break

        page_number += 1

    return all_posts, includes