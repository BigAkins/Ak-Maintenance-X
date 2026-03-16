import json
import requests

TOKEN_FILE = "token.json"
ME_URL = "https://api.x.com/2/users/me"


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


def get_me(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = requests.get(ME_URL, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def main():
    print("Loading access token from token.json ...")
    access_token = load_access_token()

    print("Calling GET /2/users/me ...")
    me_data = get_me(access_token)

    user = me_data["data"]

    print("\nSuccess! Your account info:")
    print(f"Name: {user.get('name')}")
    print(f"Username: @{user.get('username')}")
    print(f"User ID: {user.get('id')}")


if __name__ == "__main__":
    main()