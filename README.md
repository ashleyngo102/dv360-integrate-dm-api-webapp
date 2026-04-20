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


## `deploy.sh`

### Usage

1.  **Defaults**: The script comes with predefined default values for `SERVICE_NAME`, `PROJECT_ID`, `BUCKET_NAME`, and `REGION`.
2.  **Interactive Configuration**: When run, it prompts you to confirm or change these deployment configuration values. You can hit `Enter` to accept the defaults for each prompt.
3.  **GCS Bucket Creation**: It attempts to create the specified GCS bucket (`gsutil mb`) in your chosen project and region. It will silently succeed if the bucket already exists.
4.  **Cloud Run Deployment**: It then deploys the service to Google Cloud Run using the `gcloud run deploy` command.
    -   It deploys the source code from the current directory (`.`).
    -   Uses a specified `SERVICE_ACCOUNT` for deployment.
    -   Sets a `timeout` of 3600 seconds, `memory` to 4Gi, and `cpu` to 2.
    -   Deploys without allowing unauthenticated access (`--no-allow-unauthenticated`).
    -   Sets environment variables `PROJECT_ID`, `GCS_BUCKET`, and `ENV` for your application to use at runtime.

### How to Run

Simply execute the script in your terminal:

```bash
bash deploy.sh
