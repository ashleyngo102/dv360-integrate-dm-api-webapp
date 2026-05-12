# Automated OAuth 2.0 Setup Guide

This project now supports automated Google OAuth 2.0 token refreshing. You no longer need to use the OAuth Playground manually.

## Prerequisites
- `requests`
- `python-dotenv`

Install them via pip:
```bash
pip install requests python-dotenv
```

## Step 1: Initial Setup (One-time)
Run the refresh token generator script:
```bash
python get_refresh_token.py
```
1. It will provide a URL. Open it in your browser and authorize access.
2. You will be redirected to `localhost`. Copy the **entire URL** from your browser's address bar (even if the page looks broken).
3. Paste that URL back into the script.
4. The script will output your `refresh_token`.

## Step 2: Configure Environment
Create a `.env` file in the `integrate-dm-api` directory:
```env
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REFRESH_TOKEN=your_generated_refresh_token
```

## Step 3: Usage
1. Start your FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```
2. Open the UI (`dv360_audience_manager.html`).
3. In **Step 2 (DV360 Target)**, leave the **Google OAuth Access Token** field as `auto`.
4. The backend will now automatically handle token refreshing for every request.

## Multi-Client Support
The UI and Backend are fully dynamic. Simply enter the relevant **Partner ID**, **Advertiser ID**, and **Audience List ID** in the web interface for each client. The automated token flow will use the credentials in your `.env` file to authorize these requests.
