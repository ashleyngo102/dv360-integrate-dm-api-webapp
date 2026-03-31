# DV360 Audience Manager Integration

This project provides a stateless FastAPI microservice and a web frontend to ingest audience list data into Display & Video 360 (DV360) using the Data Manager API.

## Features
- **Stateless Backend**: Acts as a pass-through to Google's Data Manager API.
- **Dynamic Payload Construction**: Supports Partner and Advertiser level destinations.
- **CSV Parsing**: Handles client-side CSV parsing.
- **Secure Handling**: No sensitive data is logged; simple pass-through.

## Prerequisites
- Python 3.9+
- pip (Python package installer)

## Installation

1.  **Clone the Repository** and navigate to this directory.
2.  **Install Dependencies**:
    ```bash
    pip install fastapi uvicorn requests pydantic
    ```

## Running Locally

### 1. Start the FastAPI Backend
Initialize your microservice to accept ingress queries:
```bash
python3 -m uvicorn main:app --reload --port 8000
```
*(The server will run on `http://localhost:8000/`)*

### 2. Launch the Web Frontend
Navigating to the served root address will load the interactive elements instead of file-caching!
Open your web browser directly to:
```bash
http://localhost:8000/
```

## How to Test

1.  **Acquire Access Tone**: 
    - Go to [Google OAuth 2.0 Playground](https://developers.google.com/oauthplayground/).
    - Enter scope: `https://www.googleapis.com/auth/datamanager`.
    - Click "Authorize APIs" and exchange the authentication authorization code.
2.  **Input Details on the Frontend**: Complete the fields (Bearer Token, Partner ID, Advertiser ID, Audience ID (Destination), CSV upload).
3.  **Push Data**: Click "Push to DV360".

### Checking Request Status
You can trace specific upload events using this automated helper script:
```bash
python3 check_status.py <requestId>
```
*(Optionally include the access token as a subsequent argument if yours expired).*
