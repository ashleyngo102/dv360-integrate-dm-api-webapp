import os
import hashlib
import re
import requests
import zipfile
import io
import xml.etree.ElementTree as ET
import csv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from auth_utils import get_access_token
from urllib.parse import urlencode

def clean_header_fuzzy(h: str) -> str:
    return re.sub(r'[^a-z0-9]', '', str(h).lower())

def clean_header(h: str) -> str:
    return clean_header_fuzzy(h)

def parse_xlsx_manual(file_bytes: bytes) -> List[dict]:
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            file_list = z.namelist()
            print(f"Files in XLSX ZIP: {file_list}")
            
            try:
                shared_strings_xml = z.read('xl/sharedStrings.xml')
                root_strings = ET.fromstring(shared_strings_xml)
                ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                strings = [t.text for t in root_strings.findall('.//ns:t', ns)]
            except KeyError:
                strings = []

            sheet_path = 'xl/worksheets/sheet1.xml'
            if sheet_path not in file_list:
                sheet_files = [f for f in file_list if f.startswith('xl/worksheets/sheet') and f.endswith('.xml')]
                if sheet_files:
                    sheet_path = sheet_files[0]
                    print(f"Using sheet: {sheet_path}")
                else:
                    print("No sheet found in xl/worksheets/")
                    return []
            
            sheet_xml = z.read(sheet_path)
            root_sheet = ET.fromstring(sheet_xml)
            
            rows = []
            for r in root_sheet.findall('.//ns:row', ns):
                row_data = []
                for c in r.findall('.//ns:c', ns):
                    v = c.find('ns:v', ns)
                    if v is None:
                        row_data.append('')
                        continue
                    v_text = v.text
                    if c.get('t') == 's':
                        try:
                            idx = int(v_text)
                            if idx < len(strings):
                                row_data.append(strings[idx])
                            else:
                                row_data.append('')
                        except (ValueError, TypeError):
                            row_data.append('')
                    else:
                        row_data.append(v_text)
                rows.append(row_data)
        
        if not rows:
            return []
            
        headers = [str(col).strip() for col in rows[0]]
        records = []
        for row in rows[1:]:
            if not any(row): continue
            record = {}
            for i, h in enumerate(headers):
                if i < len(row):
                    record[h] = str(row[i]).strip()
                else:
                    record[h] = ''
            records.append(record)
        return records

    except zipfile.BadZipFile:
        try:
            text = file_bytes.decode('utf-8')
            f = io.StringIO(text)
            reader = csv.DictReader(f)
            return list(reader)
        except Exception as e:
            print(f"Fallback to CSV parsing failed: {e}")
            return []
    except Exception as e:
        import traceback
        print(f"Error parsing XLSX: {traceback.format_exc()}")
        return []

def download_sheet_as_csv(url: str, token: str) -> Optional[bytes]:
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
    if not match:
        return None

    spreadsheet_id = match.group(1)
    export_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(export_url, headers=headers)

    if response.status_code == 200:
        return response.content

    print(f"Sheet download failed: {response.status_code} - {response.text}")
    return None

app = FastAPI(title="DV360 Data Manager Pass-Through (Stateless)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import HTMLResponse

def resolve_token(token: str) -> str:
    """If token is 'auto' or empty, try to get it from auth_utils."""
    if not token or token.lower() == "auto":
        automated_token = get_access_token()
        if isinstance(automated_token, dict): # Error case
            raise HTTPException(status_code=401, detail=f"Automated token refresh failed: {automated_token.get('details')}")
        return automated_token
    return token

@app.get("/auth/url")
async def get_auth_url(request: Request):
    """Generates the Google OAuth URL for the frontend."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not set in .env")
    
    # Use REDIRECT_URI from .env if available, otherwise fallback to request base_url
    redirect_uri = os.getenv("REDIRECT_URI")
    if not redirect_uri:
        base_url = str(request.base_url).rstrip("/")
        redirect_uri = f"{base_url}/auth/callback"
    
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "https://www.googleapis.com/auth/datamanager",
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent"
    }
    return {"url": f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"}

@app.get("/auth/status")
async def get_auth_status():
    """Checks if the application is configured with valid OAuth credentials."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        return {
            "status": "missing_config",
            "details": "One or more OAuth credentials (Client ID, Secret, Refresh Token) are missing from .env"
        }

    # Attempt a dry-run refresh
    token_res = get_access_token()
    if isinstance(token_res, dict) and "error" in token_res:
        return {
            "status": "unauthorized",
            "details": token_res.get("details", "Failed to refresh token")
        }
    
    return {
        "status": "authenticated",
        "message": "Application is successfully authenticated with Google."
    }

@app.get("/auth/callback")
async def auth_callback(request: Request, code: str):
    """Handles the redirect from Google and saves the refresh token."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    # Use REDIRECT_URI from .env if available, otherwise fallback to request base_url
    redirect_uri = os.getenv("REDIRECT_URI")
    if not redirect_uri:
        base_url = str(request.base_url).rstrip("/")
        redirect_uri = f"{base_url}/auth/callback"
    
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    
    res = requests.post(token_url, data=data)
    if res.status_code != 200:
        return HTMLResponse(content=f"<h1>Auth Failed</h1><pre>{res.text}</pre>")
    
    tokens = res.json()
    refresh_token = tokens.get("refresh_token")
    
    if refresh_token:
        # Update the .env file automatically
        with open(".env", "r") as f:
            lines = f.readlines()
        
        with open(".env", "w") as f:
            for line in lines:
                if line.startswith("GOOGLE_REFRESH_TOKEN="):
                    f.write(f"GOOGLE_REFRESH_TOKEN={refresh_token}\n")
                else:
                    f.write(line)
        
        return HTMLResponse(content="<h1>Authentication Successful!</h1><p>The refresh token has been saved. You can close this tab and return to the app.</p>")
    
    return HTMLResponse(content="<h1>Warning</h1><p>Auth worked, but no refresh token was returned. (You might have already authorized recently). Try again or check your .env.</p>")

@app.get("/", response_class=HTMLResponse)
async def get_ui():
    html_path = os.path.join(os.getcwd(), 'dv360_audience_manager.html')
    try:
        with open(html_path, 'r') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>HTML File Not Found</h1>", status_code=404)

class Member(BaseModel):
    email: str
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    match_id: Optional[str] = None

class AudienceUpload(BaseModel):
    access_token: Optional[str] = "auto"
    partner_id: Optional[str] = None
    advertiser_id: Optional[str] = None
    user_list_id: str
    member_list: List[Member]

def is_sha256(s: str) -> bool:
    return bool(re.match(r'^[a-fA-F0-9]{64}$', s.strip()))

def format_and_hash(val: str, field_type: str = 'string') -> str:
    if not val:
        return val
    val = val.strip()
    if is_sha256(val):
        return val.lower()
    if field_type in ['email', 'first_name', 'last_name']:
        val = val.lower()
    return hashlib.sha256(val.encode('utf-8')).hexdigest()

def prepare_payload_and_ingest(members: List[Member], access_token: str, user_list_id: str, partner_id: Optional[str] = None, advertiser_id: Optional[str] = None):
    try:
        audience_members = []
        for mem in members:
            identifiers = []
            if mem.email:
                identifiers.append({ "emailAddress": format_and_hash(mem.email, 'email') })
            if mem.phone:
                identifiers.append({ "phoneNumber": format_and_hash(mem.phone, 'phone') })
            if hasattr(mem, 'match_id') and mem.match_id:
                identifiers.append({ "thirdPartyUserId": mem.match_id.strip() })
            if mem.first_name and mem.last_name:
                address_info = {
                    "givenName": format_and_hash(mem.first_name, 'first_name'),
                    "familyName": format_and_hash(mem.last_name, 'last_name'),
                }
                if mem.zip_code:
                    address_info["postalCode"] = mem.zip_code.strip()
                if mem.country:
                    address_info["regionCode"] = mem.country.strip()
                identifiers.append({ "address": address_info })
            
            if identifiers:
                audience_members.append({"userData": {"userIdentifiers": identifiers}})

        if not audience_members:
             raise HTTPException(status_code=400, detail="No valid audience members to ingest.")

        destination = {
            "productDestinationId": user_list_id
        }
        
        if partner_id and advertiser_id:
             destination["operatingAccount"] = {"accountType": "DISPLAY_VIDEO_ADVERTISER", "accountId": advertiser_id}
             destination["loginAccount"] = {"accountType": "DISPLAY_VIDEO_PARTNER", "accountId": partner_id}
        elif advertiser_id:
             destination["operatingAccount"] = {"accountType": "DISPLAY_VIDEO_ADVERTISER", "accountId": advertiser_id}
        elif partner_id:
             destination["operatingAccount"] = {"accountType": "DISPLAY_VIDEO_PARTNER", "accountId": partner_id}
        else:
             raise HTTPException(status_code=400, detail="Either partner_id or advertiser_id must be provided")

        payload = {
            "destinations": [destination],
            "audienceMembers": audience_members,
            "encoding": "HEX",
            "termsOfService": {"customerMatchTermsOfServiceStatus": "ACCEPTED"},
            "consent": {"adUserData": "CONSENT_GRANTED", "adPersonalization": "CONSENT_GRANTED"}
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        endpoint = "https://datamanager.googleapis.com/v1/audienceMembers:ingest"
        response = requests.post(endpoint, json=payload, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
        return response.json()
    except HTTPException as e:
        raise e
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Request to Data Manager API failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Server is running"}

@app.post("/upload-audience")
async def upload_audience(request: AudienceUpload):
    token = resolve_token(request.access_token)
    res = prepare_payload_and_ingest(request.member_list, token, request.user_list_id, request.partner_id, request.advertiser_id)
    return {
        "status": "success", 
        "request_id": res.get("requestId"),
        "message": f"Data successfully submitted for {len(request.member_list)} members. Use the request_id to check status."
    }

@app.post("/upload-audience-file")
async def upload_audience_file(
    file: Optional[UploadFile] = File(None),
    google_sheet_url: Optional[str] = Form(None),
    access_token: str = Form("auto"),
    partner_id: Optional[str] = Form(None),
    advertiser_id: Optional[str] = Form(None),
    user_list_id: Optional[str] = Form(None)
):
    try:
        access_token = resolve_token(access_token)
        if not user_list_id or user_list_id.strip() == "":
            if not advertiser_id:
                 raise HTTPException(status_code=400, detail="Cannot create UserList without advertiser_id. Please provide either user_list_id or advertiser_id.")
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            create_url = f"https://datamanager.googleapis.com/v1/accountTypes/DISPLAY_VIDEO_ADVERTISER/accounts/{advertiser_id}/userLists"
            create_body = {
                "displayName": "Uploaded_Audience_List_2026",
                "membershipDuration": "2592000s",
                "ingestedUserListInfo": {
                    "uploadKeyTypes": ["CONTACT_ID"]
                }
            }
            print(f"Creating UserList at: {create_url}")
            create_res = requests.post(create_url, json=create_body, headers=headers)
            if create_res.status_code != 200:
                raise HTTPException(status_code=create_res.status_code, detail=f"Failed to create UserList: {create_res.text}")
            
            create_data = create_res.json()
            user_list_id = create_data.get("id")
            if not user_list_id:
                raise HTTPException(status_code=500, detail="UserList created but no ID returned in response.")
            print(f"Created new UserList with ID: {user_list_id}")

        file_bytes = None
        records = []
        
        if google_sheet_url:
            file_bytes = download_sheet_as_csv(google_sheet_url, access_token)
            if not file_bytes:
                raise HTTPException(status_code=400, detail="Could not download Google Sheet. Ensure it is visible to 'Anyone with the link can view'.")
            text = file_bytes.decode('utf-8')
            f = io.StringIO(text)
            reader = csv.DictReader(f)
            records = list(reader)
        elif file:
            file_bytes = await file.read()
            if file.filename.endswith('.csv'):
                text = file_bytes.decode('utf-8')
                f = io.StringIO(text)
                reader = csv.DictReader(f)
                records = list(reader)
            elif file.filename.endswith('.xlsx'):
                records = parse_xlsx_manual(file_bytes)
            else:
                raise HTTPException(status_code=400, detail="Unsupported file format. Only .csv and .xlsx are supported.")
        else:
            raise HTTPException(status_code=400, detail="No file or Google Sheet URL provided.")

        if not records:
             raise HTTPException(status_code=400, detail="File is empty or could not be parsed.")

        active_keys = records[0].keys()
        headers_cleaned = {clean_header_fuzzy(k): k for k in active_keys}
        
        col_map = {
            "email": None, "phone": None, "first_name": None,
            "last_name": None, "zip_code": None, "country": None,
            "match_id": None
        }
        
        for ck, k in headers_cleaned.items():
            if "email" in ck or "mail" in ck: col_map["email"] = k
            elif "phone" in ck or "mobile" in ck or "cell" in ck or "tel" in ck: col_map["phone"] = k
            elif "first" in ck or "given" in ck or "fname" in ck or "first_name" in ck: col_map["first_name"] = k
            elif "last" in ck or "family" in ck or "lname" in ck or "surname" in ck or "last_name" in ck: col_map["last_name"] = k
            elif "zip" in ck or "postal" in ck or "postcode" in ck or "zip_code" in ck: col_map["zip_code"] = k
            elif "country" in ck or "region" in ck or "nation" in ck: col_map["country"] = k
            elif "matchid" in ck or "match_id" in ck: col_map["match_id"] = k

        if not col_map["email"] and active_keys:
             col_map["email"] = list(active_keys)[0]

        members = []
        for rec in records:
            member_data = {}
            if col_map["email"] and rec.get(col_map["email"]): member_data["email"] = rec[col_map["email"]]
            if col_map["phone"] and rec.get(col_map["phone"]): member_data["phone"] = rec[col_map["phone"]]
            if col_map["first_name"] and rec.get(col_map["first_name"]): member_data["first_name"] = rec[col_map["first_name"]]
            if col_map["last_name"] and rec.get(col_map["last_name"]): member_data["last_name"] = rec[col_map["last_name"]]
            if col_map["zip_code"] and rec.get(col_map["zip_code"]): member_data["zip_code"] = rec[col_map["zip_code"]]
            if col_map["country"] and rec.get(col_map["country"]): member_data["country"] = rec[col_map["country"]]
            if col_map.get("match_id") and rec.get(col_map["match_id"]): member_data["match_id"] = rec[col_map["match_id"]]
            
            if member_data.get("email"):
                 members.append(Member(**member_data))

        if not members:
            raise HTTPException(status_code=400, detail="No members with valid emails found.")

        res = prepare_payload_and_ingest(members, access_token, user_list_id, partner_id, advertiser_id)
        return {
            "status": "success", 
            "request_id": res.get("requestId"),
            "message": f"Data successfully submitted for {len(members)} members. Use the request_id to check status."
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
