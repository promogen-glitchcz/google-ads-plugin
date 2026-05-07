#!/usr/bin/env python3
"""
OAuth setup wizard for Google Ads API.

Generates a fresh refresh token using a local-server OAuth flow.
The OAuth client must have http://localhost:8765 in authorized redirect URIs.
"""
import http.server
import json
import os
import socketserver
import sys
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".secrets" / ".env"
PORT = 8765
REDIRECT_URI = f"http://localhost:{PORT}"
SCOPE = "https://www.googleapis.com/auth/adwords"


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def load_env():
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def write_env(env):
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{k}={v}" for k, v in env.items()]
    ENV_PATH.write_text("\n".join(lines) + "\n")


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    auth_code = None
    error = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            CallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body style='font-family:sans-serif;text-align:center;padding:40px'>"
                b"<h1>Hotovo! Mozes zatvorit toto okno.</h1>"
                b"<p>Refresh token bol ulozeny do .secrets/.env</p></body></html>"
            )
        elif "error" in params:
            CallbackHandler.error = params["error"][0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<h1>Chyba: {CallbackHandler.error}</h1>".encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *_):
        pass


def main():
    env = load_env()
    client_id = env.get("GOOGLE_ADS_CLIENT_ID")
    client_secret = env.get("GOOGLE_ADS_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("ERROR: chyba GOOGLE_ADS_CLIENT_ID alebo GOOGLE_ADS_CLIENT_SECRET v .secrets/.env")
        sys.exit(1)

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + urllib.parse.urlencode(
            {
                "client_id": client_id,
                "redirect_uri": REDIRECT_URI,
                "response_type": "code",
                "scope": SCOPE,
                "access_type": "offline",
                "prompt": "consent",
            }
        )
    )

    print("\n=== Google Ads OAuth Setup ===\n")
    print("1. Otvor tento link v prehliadaci (alebo to spravim za teba):")
    print(f"\n{auth_url}\n")
    print(f"2. Po prihlaseni Google presmeruje na localhost:{PORT}")
    print("3. Token sa automaticky ulozi.\n")

    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    with ReusableTCPServer(("", PORT), CallbackHandler) as httpd:
        print(f"Cakam na callback na http://localhost:{PORT} ...")
        while CallbackHandler.auth_code is None and CallbackHandler.error is None:
            httpd.handle_request()

    if CallbackHandler.error:
        print(f"OAuth chyba: {CallbackHandler.error}")
        sys.exit(1)

    code = CallbackHandler.auth_code
    print("Autorizacny kod prijaty, vymienam za refresh token...")

    data = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        }
    ).encode()

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            tok = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"Token exchange zlyhal: {e.read().decode()}")
        sys.exit(1)

    refresh = tok.get("refresh_token")
    access = tok.get("access_token")
    if not refresh:
        print("WARN: Google nevratil refresh_token (mozno mas existujuci grant).")
        print("Idem na https://myaccount.google.com/permissions revokovat a skus znova.")
        sys.exit(1)

    env["GOOGLE_ADS_REFRESH_TOKEN"] = refresh
    write_env(env)

    print("\nUSPECH! Refresh token ulozeny do .secrets/.env")
    print(f"Access token (TTL ~1h): {access[:20]}...")
    print("\nDalsi krok: python3 scripts/list_accounts.py")


if __name__ == "__main__":
    main()
