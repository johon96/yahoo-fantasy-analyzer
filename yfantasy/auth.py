"""OAuth2 authentication for Yahoo Fantasy Sports API."""

from __future__ import annotations

import base64
import logging
import os
import ssl
import subprocess
import tempfile
import threading
import webbrowser
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from yfantasy.config import Config

logger = logging.getLogger(__name__)

_AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
_USERINFO_URL = "https://api.login.yahoo.com/openid/v1/userinfo"
_CALLBACK_PORT = 8765


def _create_ssl_context() -> ssl.SSLContext:
    """Create an SSL context with a throwaway self-signed cert for localhost."""
    tmpdir = tempfile.mkdtemp()
    certfile = os.path.join(tmpdir, "cert.pem")
    keyfile = os.path.join(tmpdir, "key.pem")
    try:
        subprocess.run(
            [
                "openssl", "req", "-x509", "-newkey", "rsa:2048",
                "-keyout", keyfile, "-out", certfile,
                "-days", "1", "-nodes", "-subj", "/CN=localhost",
            ],
            capture_output=True,
            check=True,
        )
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile, keyfile)
        return ctx
    finally:
        for f in (certfile, keyfile):
            if os.path.exists(f):
                os.unlink(f)
        os.rmdir(tmpdir)


class YahooAuth:
    """Handles Yahoo OAuth2 flow and token management."""

    def __init__(self, config: Config):
        self.config = config

    def needs_init(self) -> bool:
        return not self.config.has_credentials() or not self.config.has_token()

    def get_access_token(self) -> str:
        """Return a valid access token, refreshing if necessary."""
        if not self.config.is_token_expired():
            return self.config.get("auth", "access_token")

        # Try refresh
        refresh_token = self.config.get("auth", "refresh_token")
        if not refresh_token:
            raise RuntimeError("No refresh token. Run `yfantasy init` to authenticate.")

        logger.info("Access token expired, refreshing...")
        token_data = self._refresh(refresh_token)
        self._store_token(token_data)
        return token_data["access_token"]

    def run_oauth_flow(self) -> dict:
        """Run full OAuth2 browser flow. Returns token data dict."""
        client_id = self.config.get("auth", "client_id")
        redirect_uri = f"https://localhost:{_CALLBACK_PORT}"

        params = urlencode({
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
        })
        auth_url = f"{_AUTH_URL}?{params}"

        code = self._capture_auth_code(auth_url, redirect_uri)
        token_data = self._exchange_code(code, redirect_uri)
        self._store_token(token_data)
        return token_data

    def get_user_info(self) -> dict:
        """Fetch Yahoo user profile (guid, email, name)."""
        token = self.get_access_token()
        resp = requests.get(
            _USERINFO_URL, headers={"Authorization": f"Bearer {token}"}
        )
        resp.raise_for_status()
        return resp.json()

    # -- internal ------------------------------------------------------------

    def _exchange_code(self, code: str, redirect_uri: str) -> dict:
        client_id = self.config.get("auth", "client_id")
        client_secret = self.config.get("auth", "client_secret")

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        resp = requests.post(
            _TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # Fallback to Basic auth if POST body creds fail
        if not resp.ok and resp.status_code == 401:
            logger.debug("Retrying token exchange with Basic auth header")
            creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            resp = requests.post(
                _TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {creds}",
                },
            )

        resp.raise_for_status()
        return resp.json()

    def _refresh(self, refresh_token: str) -> dict:
        client_id = self.config.get("auth", "client_id")
        client_secret = self.config.get("auth", "client_secret")

        resp = requests.post(
            _TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if not resp.ok:
            raise RuntimeError(
                f"Token refresh failed ({resp.status_code}). Run `yfantasy init` to re-authenticate."
            )
        return resp.json()

    def _store_token(self, token_data: dict) -> None:
        expiry = datetime.now() + timedelta(seconds=token_data.get("expires_in", 3600))
        self.config.set("auth", "access_token", token_data["access_token"])
        self.config.set(
            "auth",
            "refresh_token",
            token_data.get("refresh_token", self.config.get("auth", "refresh_token")),
        )
        self.config.set("auth", "token_expiry", expiry.isoformat())
        self.config.save()

    def _capture_auth_code(self, auth_url: str, redirect_uri: str) -> str:
        """Open browser for auth, capture the callback code."""
        code_holder: dict[str, Optional[str]] = {"code": None}

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                qs = parse_qs(urlparse(self.path).query)
                code_holder["code"] = qs.get("code", [None])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h2>Authenticated! You can close this tab.</h2></body></html>"
                )

            def log_message(self, format, *args):
                pass  # Suppress request logs

        server = HTTPServer(("localhost", _CALLBACK_PORT), CallbackHandler)
        server.socket = _create_ssl_context().wrap_socket(
            server.socket, server_side=True
        )
        server.timeout = 5

        webbrowser.open(auth_url)

        # Loop because failed TLS handshakes (self-signed cert) consume
        # handle_request() calls without delivering actual HTTP requests.
        deadline = datetime.now() + timedelta(seconds=300)
        while not code_holder["code"] and datetime.now() < deadline:
            server.handle_request()
        server.server_close()

        if not code_holder["code"]:
            raise RuntimeError("Did not receive authorization code from Yahoo.")
        return code_holder["code"]
