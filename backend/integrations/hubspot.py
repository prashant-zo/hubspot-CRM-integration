# hubspot.py

import json
import secrets
from urllib.parse import urlencode
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import base64

from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx

from redis_client import add_key_value_redis, get_value_redis, delete_key_redis
from integrations.integration_item import IntegrationItem

# --- Constants ---
HUBSPOT_API_BASE_URL = "https://api.hubapi.com"

# TODO: In a production environment, these should be loaded from environment variables or a secure config.
HUBSPOT_CLIENT_ID = '' 
HUBSPOT_CLIENT_SECRET = '' 

HUBSPOT_REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
HUBSPOT_SCOPES = 'oauth crm.objects.contacts.read crm.schemas.contacts.read' 

HUBSPOT_AUTHORIZATION_URL = 'https://app.hubspot.com/oauth/authorize'
HUBSPOT_TOKEN_URL = 'https://api.hubapi.com/oauth/v1/token'

# --- OAuth Functions ---

async def authorize_hubspot(user_id: str, org_id: str) -> str:
    state_data = {
        'state': secrets.token_urlsafe(32), 
        'user_id': user_id,
        'org_id': org_id
    }
    
    json_state_data = json.dumps(state_data)
    base64_encoded_state = base64.urlsafe_b64encode(json_state_data.encode('utf-8')).decode('utf-8')

    redis_key_state = f'hubspot_state:{org_id}:{user_id}'
    await add_key_value_redis(redis_key_state, json_state_data, expire=600) # Storing original JSON

    auth_params = {
        'client_id': HUBSPOT_CLIENT_ID,
        'redirect_uri': HUBSPOT_REDIRECT_URI,
        'scope': HUBSPOT_SCOPES,
        'state': base64_encoded_state,
        'response_type': 'code'
    }

    authorization_url_with_params = f"{HUBSPOT_AUTHORIZATION_URL}?{urlencode(auth_params)}"
    return authorization_url_with_params



async def oauth2callback_hubspot(request: Request) -> HTMLResponse:
    code = request.query_params.get('code')
    base64_encoded_incoming_state = request.query_params.get('state')

    if request.query_params.get('error'):
        error_description = request.query_params.get('error_description', 'Unknown HubSpot OAuth error')
        # Log the detailed error on the server if needed
        print(f"ERROR: HubSpot OAuth Error received: {error_description} for state: {base64_encoded_incoming_state}")
        raise HTTPException(status_code=400, detail="HubSpot authentication failed.")
    
    if not code or not base64_encoded_incoming_state:
        raise HTTPException(status_code=400, detail="Missing required parameters in HubSpot callback.")
    
    try:
        json_incoming_state_str = base64.urlsafe_b64decode(base64_encoded_incoming_state).decode('utf-8')
        incoming_state_data = json.loads(json_incoming_state_str)
        original_random_state = incoming_state_data.get('state')
        user_id = incoming_state_data.get('user_id')
        org_id = incoming_state_data.get('org_id')

        if not all([original_random_state, user_id, org_id]):
            raise HTTPException(status_code=400, detail="Invalid state data received after decoding.")
    except (json.JSONDecodeError, base64.binascii.Error, UnicodeDecodeError) as e:
        print(f"ERROR: Malformed state parameter during HubSpot callback: {str(e)}")
        raise HTTPException(status_code=400, detail="Malformed state parameter received from HubSpot.")

    redis_key_state = f'hubspot_state:{org_id}:{user_id}'
    saved_json_state_str_bytes = await get_value_redis(redis_key_state) 

    if not saved_json_state_str_bytes:
        raise HTTPException(status_code=400, detail="HubSpot OAuth state not found or expired. Please try again.")
    
    saved_json_state_str = saved_json_state_str_bytes.decode('utf-8')

    try:
        saved_state_data = json.loads(saved_json_state_str)
    except json.JSONDecodeError:
        print(f"ERROR: Could not decode stored OAuth state from Redis. Key: {redis_key_state}")
        await delete_key_redis(redis_key_state) # Clean up corrupted key
        raise HTTPException(status_code=500, detail="Internal error processing OAuth state.")
    
    if original_random_state != saved_state_data.get('state'):
        await delete_key_redis(redis_key_state)
        raise HTTPException(status_code=400, detail="HubSpot OAuth state mismatch. Please try again.")
        
    token_payload = {
        'grant_type': 'authorization_code',
        'client_id': HUBSPOT_CLIENT_ID,
        'client_secret': HUBSPOT_CLIENT_SECRET,
        'redirect_uri': HUBSPOT_REDIRECT_URI,
        'code': code,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                HUBSPOT_TOKEN_URL,
                data=token_payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            response.raise_for_status()
            token_data = response.json()
        except httpx.HTTPStatusError as e:
            error_detail = f"HubSpot token exchange API request failed with status {e.response.status_code}."
            try: error_body = e.response.json(); error_detail += f" Response: {error_body}"
            except json.JSONDecodeError: error_detail += f" Response: {e.response.text}"
            print(f"ERROR: {error_detail}")
            await delete_key_redis(redis_key_state)
            raise HTTPException(status_code=502, detail="Failed to communicate with HubSpot for token exchange.") # 502 Bad Gateway
        except Exception as e:
            print(f"ERROR: Unexpected error during HubSpot token exchange: {str(e)}")
            await delete_key_redis(redis_key_state)
            raise HTTPException(status_code=500, detail="An unexpected error occurred during token exchange.")
        
    redis_key_credentials = f'hubspot_credentials:{org_id}:{user_id}'
    token_data['received_at'] = int(datetime.utcnow().timestamp())
    
    await add_key_value_redis(
        redis_key_credentials,
        json.dumps(token_data),
        expire=token_data.get('expires_in', 3600)
    )
    await delete_key_redis(redis_key_state)

    close_window_script = """
    <html><head><title>HubSpot Authentication Successful</title></head>
    <body><p>Authentication successful! You can close this window.</p>
    <script>if(window.opener){window.opener.postMessage('hubspotIntegrationSuccess','*');}window.close();</script></body></html>
    """
    return HTMLResponse(content=close_window_script)


async def get_hubspot_credentials(user_id: str, org_id: str) -> Dict[str, Any]:
    redis_key_credentials = f'hubspot_credentials:{org_id}:{user_id}'
    credentials_bytes = await get_value_redis(redis_key_credentials)

    if not credentials_bytes:
        raise HTTPException(status_code=404, detail="HubSpot credentials not found. Please re-authorize.")
    
    try:
        credentials_str = credentials_bytes.decode('utf-8')
        credentials = json.loads(credentials_str)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        print(f"ERROR: Could not decode stored HubSpot credentials. Key: {redis_key_credentials}, Error: {str(e)}")
        await delete_key_redis(redis_key_credentials) # Clean up malformed key
        raise HTTPException(status_code=500, detail="Error processing stored HubSpot credentials.")
    
    await delete_key_redis(redis_key_credentials) 
    return credentials



# --- HubSpot Data Fetching Functions ---

def parse_hubspot_date(date_string: Optional[str]) -> Optional[datetime]:
    if not date_string:
        return None
    try:
        if date_string.endswith('Z'): # Python < 3.11 fromisoformat might not handle 'Z' well
            date_string = date_string[:-1] + '+00:00'
        dt_object = datetime.fromisoformat(date_string)
        return dt_object.astimezone(timezone.utc) # Ensure UTC
    except ValueError:
        # Log this warning for server admin, but don't break the flow for one bad date
        print(f"Warning: Could not parse date string '{date_string}'")
        return None
    

async def get_items_hubspot(credentials_json_str: str) -> List[IntegrationItem]:
    try:
        credentials_data = json.loads(credentials_json_str)
    except json.JSONDecodeError:
        # Log part of the string for diagnostics if needed, but not in user-facing error
        print(f"ERROR: Could not decode credentials JSON string in get_items_hubspot.")
        raise HTTPException(status_code=400, detail="Invalid credentials format.")

    access_token = credentials_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Missing access token in credentials.")

    integration_items: List[IntegrationItem] = []
    properties_to_fetch = ["hs_object_id", "firstname", "lastname", "email", "createdate", "lastmodifieddate", "lifecyclestage"]
    contacts_url = f"{HUBSPOT_API_BASE_URL}/crm/v3/objects/contacts"
    headers = {"Authorization": f"Bearer {access_token}"}
    current_params = {"limit": 10, "properties": ",".join(properties_to_fetch)}
    
    all_fetched_contacts_data: List[Dict[str, Any]] = []
    page_count = 0
    max_pages = 10 # Safety limit for pagination

    async with httpx.AsyncClient() as client:
        while page_count < max_pages:
            page_count += 1
            try:
                response = await client.get(contacts_url, headers=headers, params=current_params)
                response.raise_for_status()
                response_data = response.json()
                
                page_results = response_data.get("results", [])
                all_fetched_contacts_data.extend(page_results)

                paging_next = response_data.get("paging", {}).get("next")
                if paging_next and paging_next.get("after"):
                    current_params["after"] = paging_next["after"]
                else:
                    break # No more pages
            except httpx.HTTPStatusError as e:
                error_detail = f"HubSpot API request for contacts failed: {e.response.status_code}."
                try: error_body = e.response.json(); error_detail += f" Details: {error_body}"
                except json.JSONDecodeError: error_detail += f" Body: {e.response.text}"
                print(f"ERROR: {error_detail}")
                break 
            except Exception as e:
                print(f"ERROR: Unexpected error fetching HubSpot contacts: {str(e)}")
                break

    for contact_data in all_fetched_contacts_data:
        props = contact_data.get("properties", {})
        contact_id = props.get("hs_object_id")
        firstname = props.get("firstname", "")
        lastname = props.get("lastname", "")
        email = props.get("email", "")

        name_parts = [part for part in [firstname, lastname] if part and part.strip()]
        full_name = " ".join(name_parts) if name_parts else email if email else f"Contact {contact_id or 'N/A'}"

        item = IntegrationItem(
            id=f"hs_contact_{contact_id}" if contact_id else None,
            type=props.get("lifecyclestage", "HubSpot Contact"),
            name=full_name,
            creation_time=parse_hubspot_date(props.get("createdate")),
            last_modified_time=parse_hubspot_date(props.get("lastmodifieddate")),
            directory=False
        )
        integration_items.append(item)

    print(f"\n--- Final HubSpot Integration Items (Count: {len(integration_items)}) ---")
    for item_obj in integration_items:
        print(f"  ID: {item_obj.id}, Name: {item_obj.name}, Type: {item_obj.type}")
    print("------------------------------------------------------\n")

    return integration_items