import json
import requests

TOKEN_FILE = "token.json"

ME_URL = "https://api.x.com/2/users/me"
LIKES_URL = "https://api.x.com/2/users/{user_id}/liked_tweets"
FOLLOWING_URL = "https://api.x.com/2/users/{user_id}/following"


def load_access_token():
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as file:
            token_data = json.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(
            "token.json not found. Run auth_test.py first to authenticate."
        )

    access_token = token_data.get("access_token")

    if not access_token:
        raise ValueError("No access_token found in token.json")

    return access_token


def make_get_request(url, access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = requests.get(url, headers=headers, timeout=30)
    return response


def get_profile(access_token):
    response = make_get_request(ME_URL, access_token)
    response.raise_for_status()
    return response.json()["data"]


def get_likes(access_token, user_id):
    url = LIKES_URL.format(user_id=user_id)
    response = make_get_request(url, access_token)

    if response.status_code == 402:
        return {
            "success": False,
            "error_type": "payment_required",
            "message": "Liked tweets endpoint is blocked by current X API access/billing."
        }

    response.raise_for_status()
    data = response.json()

    return {
        "success": True,
        "data": data.get("data", [])
    }


def get_following(access_token, user_id):
    url = FOLLOWING_URL.format(user_id=user_id)
    response = make_get_request(url, access_token)

    if response.status_code == 402:
        return {
            "success": False,
            "error_type": "payment_required",
            "message": "Following endpoint is blocked by current X API access/billing."
        }

    response.raise_for_status()
    data = response.json()

    return {
        "success": True,
        "data": data.get("data", [])
    }


def main():
    print("Loading access token...")
    access_token = load_access_token()

    print("Fetching profile info...")
    profile = get_profile(access_token)

    user_id = profile["id"]

    print("\nProfile:")
    print(f"Name: {profile['name']}")
    print(f"Username: @{profile['username']}")
    print(f"User ID: {user_id}")

    print("\nFetching liked tweets...")
    likes_result = get_likes(access_token, user_id)

    if likes_result["success"]:
        likes = likes_result["data"]
        print(f"Found {len(likes)} liked tweets")
        for tweet in likes[:5]:
            print(f"- {tweet['text'][:80]}")
    else:
        print(f"Could not fetch liked tweets: {likes_result['message']}")

    print("\nFetching following list...")
    following_result = get_following(access_token, user_id)

    if following_result["success"]:
        following = following_result["data"]
        print(f"Following {len(following)} accounts")
        for user in following[:5]:
            print(f"- @{user['username']}")
    else:
        print(f"Could not fetch following list: {following_result['message']}")

    print("\nInspection complete.")


if __name__ == "__main__":
    main()