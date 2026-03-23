from cleanup_helpers import load_access_token, get_profile


def main():
    print("Loading access token...")
    access_token = load_access_token()

    print("Fetching authenticated user profile...")
    profile = get_profile(access_token)

    print("\nAuthenticated as:")
    print(f"Name: {profile['name']}")
    print(f"Username: @{profile['username']}")
    print(f"User ID: {profile['id']}")


if __name__ == "__main__":
    main()