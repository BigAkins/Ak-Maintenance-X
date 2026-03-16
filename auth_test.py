import os
import base64
import hashlib
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CLIENT_ID = os.getenv("X_CLIENT_ID")
REDIRECT_URI = os.getenv("X_REDIRECT_URI")

AUTH_URL = "https://x.com/i/oauth2/authorize"
TOKEN_URL = "https://api.x.com/2/oauth2/token"

SCOPES = [
    "tweet.read",
    "users.read",
    "tweet.write",
    "like.read",
    "like.write",
    "follows.read",
    "follows.write",
    "offline.access",
]

authorization_code = None
returned_error = None
returned_error_description = None


def generate_code_verifier():
    """
    PKCE code verifier:
    random high-entropy string
    """
    return secrets.token_urlsafe(64)


def generate_code_challenge(code_verifier):
    """
    PKCE code challenge:
    BASE64URL-ENCODE(SHA256(code_verifier))
    """
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global authorization_code, returned_error, returned_error_description

        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)

        if parsed_url.path == "/callback":
            authorization_code = query_params.get("code", [None])[0]
            returned_error = query_params.get("error", [None])[0]
            returned_error_description = query_params.get("error_description", [None])[0]

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            if authorization_code:
                self.wfile.write(
                    b"<h1>Authorization received successfully. You can close this tab.</h1>"
                )
            else:
                self.wfile.write(
                    b"<h1>Authorization failed. You can close this tab and check your terminal.</h1>"
                )
        else:
            self.send_response(404)
            self.end_headers()


def start_server():
    server = HTTPServer(("127.0.0.1", 8000), CallbackHandler)
    server.handle_request()


def build_auth_url(client_id, redirect_uri, scopes, state, code_challenge):
    scope_string = "%20".join(scopes)

    return (
        f"{AUTH_URL}"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scope_string}"
        f"&state={state}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )


def exchange_code_for_token(code, code_verifier):
    data = {
        "code": code,
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
    }

    response = requests.post(TOKEN_URL, data=data, timeout=30)
    response.raise_for_status()
    return response.json()


def main():
    global authorization_code, returned_error, returned_error_description

    if not CLIENT_ID:
        raise ValueError("Missing X_CLIENT_ID in .env")

    if not REDIRECT_URI:
        raise ValueError("Missing X_REDIRECT_URI in .env")

    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    state = secrets.token_urlsafe(16)

    auth_url = build_auth_url(
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scopes=SCOPES,
        state=state,
        code_challenge=code_challenge,
    )

    print("Starting local callback server on http://127.0.0.1:8000 ...")
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    print("Opening browser for X login...")
    print(auth_url)
    webbrowser.open(auth_url)

    server_thread.join()

    if returned_error:
        print("\nAuthorization failed.")
        print(f"error: {returned_error}")
        print(f"error_description: {returned_error_description}")
        return

    if not authorization_code:
        raise ValueError("No authorization code received.")

    print("\nAuthorization code received successfully!")
    print("Code:")
    print(authorization_code)

    print("\nExchanging authorization code for access token...")
    token_data = exchange_code_for_token(authorization_code, code_verifier)

    print("\nSuccess! Token response received.")
    print("Access token starts with:")
    print(token_data["access_token"][:40] + "...")

    if "refresh_token" in token_data:
        print("Refresh token received too.")

if __name__ == "__main__":
    main()