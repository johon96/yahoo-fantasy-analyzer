"""OAuth authentication for Yahoo Fantasy Sports API."""
import base64
import json
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode
import requests
from requests_oauthlib import OAuth2Session
from app.config import settings

# Path to store user tokens
TOKEN_STORAGE_PATH = Path(__file__).parent.parent / "data" / "user_tokens.json"


class User:
    """Simple User class for storing OAuth tokens."""
    
    def __init__(self, yahoo_guid: str, access_token: str, refresh_token: str, 
                 token_expires_at: datetime, id: Optional[str] = None):
        self.id = id or yahoo_guid
        self.yahoo_guid = yahoo_guid
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expires_at = token_expires_at
    
    def to_dict(self) -> dict:
        """Convert user to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "yahoo_guid": self.yahoo_guid,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_expires_at": self.token_expires_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create user from dictionary."""
        return cls(
            yahoo_guid=data["yahoo_guid"],
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            token_expires_at=datetime.fromisoformat(data["token_expires_at"]),
            id=data.get("id")
        )


class YahooOAuth:
    """Handles OAuth 2.0 authentication with Yahoo."""
    
    def __init__(self):
        self.client_id = settings.yahoo_client_id
        self.client_secret = settings.yahoo_client_secret
        self.redirect_uri = settings.yahoo_redirect_uri
        self.auth_url = settings.yahoo_auth_url
        self.token_url = settings.yahoo_token_url
        
    def get_authorization_url(self) -> tuple[str, str]:
        """Generate authorization URL and state token."""
        state = secrets.token_urlsafe(32)
        # Yahoo Fantasy Sports API - try without explicit scopes
        # Yahoo may auto-apply scopes based on app configuration
        # If scopes are needed, check your Yahoo Developer Console app settings
        oauth = OAuth2Session(
            self.client_id,
            redirect_uri=self.redirect_uri
            # No scope parameter - Yahoo will use default scopes for your app
        )
        authorization_url, _ = oauth.authorization_url(self.auth_url, state=state)
        return authorization_url, state
    
    def get_token(self, authorization_code: str) -> dict:
        """Exchange authorization code for access token."""
        # Yahoo OAuth token exchange
        # Try with credentials in POST body first (Yahoo's preferred method)
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": self.redirect_uri,  # Must match exactly what was used in authorization
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        response = requests.post(self.token_url, data=data, headers=headers)
        
        # If that fails, try with Basic Auth as fallback
        if not response.ok and response.status_code == 401:
            print("Trying with Basic Authentication as fallback...")
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            data_without_creds = {
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": self.redirect_uri,
            }
            
            headers["Authorization"] = f"Basic {encoded_credentials}"
            # Remove credentials from data if they exist (they shouldn't be there)
            if "client_id" in data_without_creds:
                del data_without_creds["client_id"]
            if "client_secret" in data_without_creds:
                del data_without_creds["client_secret"]
            
            response = requests.post(self.token_url, data=data_without_creds, headers=headers)
        
        # Log detailed error information if request fails
        if not response.ok:
            error_detail = f"Status: {response.status_code}, Response: {response.text}"
            print(f"Yahoo token exchange error: {error_detail}")
            print(f"Redirect URI: {self.redirect_uri}")
            response.raise_for_status()
        
        token = response.json()
        return token
    
    def refresh_token(self, refresh_token: str) -> dict:
        """Refresh access token using refresh token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        response = requests.post(self.token_url, data=data)
        response.raise_for_status()
        return response.json()
    
    def get_user_info(self, access_token: str) -> dict:
        """Get user information from Yahoo API."""
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            "https://api.login.yahoo.com/openid/v1/userinfo",
            headers=headers
        )
        response.raise_for_status()
        return response.json()


def _load_users() -> dict:
    """Load users from JSON file."""
    if not TOKEN_STORAGE_PATH.exists():
        TOKEN_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        return {}
    
    try:
        with open(TOKEN_STORAGE_PATH, 'r') as f:
            data = json.load(f)
            return {guid: User.from_dict(user_data) for guid, user_data in data.items()}
    except (json.JSONDecodeError, KeyError):
        return {}


def _save_users(users: dict):
    """Save users to JSON file."""
    TOKEN_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_STORAGE_PATH, 'w') as f:
        json.dump({guid: user.to_dict() for guid, user in users.items()}, f, indent=2)


def get_or_create_user(token_data: dict, user_info: dict) -> User:
    """Get or create user from JSON storage."""
    yahoo_guid = user_info.get("sub")
    users = _load_users()
    
    if yahoo_guid in users:
        user = users[yahoo_guid]
        user.access_token = token_data.get("access_token")
        user.refresh_token = token_data.get("refresh_token")
        user.token_expires_at = datetime.now() + timedelta(seconds=token_data.get("expires_in", 3600))
    else:
        user = User(
            yahoo_guid=yahoo_guid,
            access_token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_expires_at=datetime.now() + timedelta(seconds=token_data.get("expires_in", 3600))
        )
    
    users[yahoo_guid] = user
    _save_users(users)
    return user


def get_valid_access_token(user: User) -> str:
    """Get valid access token, refreshing if necessary."""
    if user.token_expires_at and datetime.now() < user.token_expires_at:
        return user.access_token
    
    # Token expired, refresh it
    oauth = YahooOAuth()
    try:
        token_data = oauth.refresh_token(user.refresh_token)
        
        # Update user object
        user.access_token = token_data.get("access_token")
        user.refresh_token = token_data.get("refresh_token", user.refresh_token)
        user.token_expires_at = datetime.now() + timedelta(seconds=token_data.get("expires_in", 3600))
        
        # Save to JSON
        users = _load_users()
        users[user.yahoo_guid] = user
        _save_users(users)
        
        return user.access_token
    except Exception as e:
        raise Exception(f"Failed to refresh token: {e}")

