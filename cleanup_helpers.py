import json
import os

import requests

from cleanup_config import (
    TOKEN_FILE,
    PROTECTED_ACCOUNTS_FILE,
    DEFAULT_KEEP_USERNAMES,
    DEFAULT_KEEP_USER_IDS,
)

ME_URL = "https://api.x.com/2/users/me"


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