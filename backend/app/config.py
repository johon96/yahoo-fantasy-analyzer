"""Configuration settings for the application."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    yahoo_client_id: str
    yahoo_client_secret: str
    yahoo_redirect_uri: str
    database_url: str = "sqlite:///./fantasy_hockey.db"
    secret_key: str
    log_level: str = "INFO"
    
    # Yahoo API endpoints
    yahoo_auth_url: str = "https://api.login.yahoo.com/oauth2/request_auth"
    yahoo_token_url: str = "https://api.login.yahoo.com/oauth2/get_token"
    yahoo_api_base_url: str = "https://fantasysports.yahooapis.com/fantasy/v2"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()

