try:
    from scripts._bootstrap import bootstrap_project_root
except ModuleNotFoundError:
    from _bootstrap import bootstrap_project_root

bootstrap_project_root()

from ak_maintenance_x.cleanup_helpers import load_access_token, get_profile


def run_get_me():
    """Load the authenticated profile and return a summary dict."""
    print("Loading access token...")
    access_token = load_access_token()

    print("Fetching authenticated user profile...")
    profile = get_profile(access_token)

    print("\nAuthenticated as:")
    print(f"Name: {profile['name']}")
    print(f"Username: @{profile['username']}")
    print(f"User ID: {profile['id']}")

    return {
        "profile": profile,
        "summary": {
            "user_id": profile["id"],
            "name": profile["name"],
            "username": profile["username"],
        },
    }


def main():
    run_get_me()


if __name__ == "__main__":
    main()
