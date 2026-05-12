import requests
import json
import os
from dotenv import load_dotenv

# Load variables from .env file if it exists
load_dotenv()

def get_access_token():
    """
    Programmatically obtains a Google OAuth 2.0 Access Token using a Refresh Token.
    Returns the token string on success, or a dictionary with 'error' and 'details' on failure.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        missing = []
        if not client_id: missing.append("GOOGLE_CLIENT_ID")
        if not client_secret: missing.append("GOOGLE_CLIENT_SECRET")
        if not refresh_token: missing.append("GOOGLE_REFRESH_TOKEN")
        return {
            "error": "Missing credentials",
            "details": f"Missing environment variables: {', '.join(missing)}"
        }

    url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }

    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code != 200:
            try:
                err_data = response.json()
                details = err_data.get("error_description", response.text)
            except:
                details = response.text
            return {
                "error": "Token Refresh Failed",
                "details": f"Google API returned {response.status_code}: {details}"
            }
        
        tokens = response.json()
        return tokens.get("access_token")
    except requests.exceptions.RequestException as e:
        return {
            "error": "Network Error",
            "details": f"Could not connect to Google OAuth server: {str(e)}"
        }
    except Exception as e:
        return {
            "error": "Internal Error",
            "details": str(e)
        }

if __name__ == "__main__":
    # If run directly, it prints the token
    token = get_access_token()
    if isinstance(token, dict):
        print(f"Error: {token['error']}")
        print(token['details'])
    else:
        print(f"Access Token: {token}")
