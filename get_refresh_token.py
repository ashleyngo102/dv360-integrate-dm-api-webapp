import requests
from urllib.parse import urlencode, parse_qs, urlparse

def generate_refresh_token():
    print("--- Google OAuth 2.0 Refresh Token Generator ---")
    client_id = input("Enter your Client ID: ").strip()
    client_secret = input("Enter your Client Secret: ").strip()
    
    # Scope for Data Manager
    scope = "https://www.googleapis.com/auth/datamanager"
    redirect_uri = "http://localhost"
    
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent"
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
    
    print("
1. Open the following URL in your browser and authorize the application:")
    print(f"
{auth_url}
")
    
    callback_url = input("2. After authorizing, you will be redirected to localhost (which might fail to load). 
   Copy the ENTIRE URL you were redirected to and paste it here: ").strip()
    
    try:
        parsed_url = urlparse(callback_url)
        code = parse_qs(parsed_url.query).get('code')[0]
    except Exception:
        print("Error: Could not find 'code' in the URL. Make sure you copied the full redirect URL.")
        return

    print("
3. Exchanging code for tokens...")
    
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    
    response = requests.post(token_url, data=data)
    
    if response.status_code == 200:
        tokens = response.json()
        refresh_token = tokens.get("refresh_token")
        print("
SUCCESS!")
        print(f"Refresh Token: {refresh_token}")
        print("
Add these to your .env file:")
        print(f"GOOGLE_CLIENT_ID={client_id}")
        print(f"GOOGLE_CLIENT_SECRET={client_secret}")
        print(f"GOOGLE_REFRESH_TOKEN={refresh_token}")
    else:
        print(f"
FAILED: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    generate_refresh_token()
