"""Creates the 'uTask Standalone (macOS)' product on Polar (pay what you want) and attaches the zip as a download.
Usage: .venv/bin/python scripts/polar-publish-standalone.py releases/utask-2.1.0-macos-arm64.zip
Token: ~/.config/polar/token (never printed). For later versions: upload the new zip, PATCH the benefit's files."""
import base64, hashlib, json, os, sys, urllib.request

TOKEN = os.environ.get("POLAR_TOKEN") or open(os.path.expanduser("~/.config/polar/token")).read().strip()
ORG = "aa792ea4-650e-492e-a955-9b3d564e943e"

def call(method, path, body=None):
    req = urllib.request.Request("https://api.polar.sh/v1" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "curl/8.7.1", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} {e.read().decode()[:800]}")

def upload(path):
    data = open(path, "rb").read()
    sha = base64.b64encode(hashlib.sha256(data).digest()).decode()
    f = call("POST", "/files/", {"name": os.path.basename(path), "mime_type": "application/zip", "size": len(data),
        "checksum_sha256_base64": sha, "service": "downloadable",
        "upload": {"parts": [{"number": 1, "chunk_start": 0, "chunk_end": len(data), "checksum_sha256_base64": sha}]}})
    part = f["upload"]["parts"][0]
    req = urllib.request.Request(part["url"], method="PUT", data=data, headers={**(part.get("headers") or {}), "User-Agent": "curl/8.7.1"})
    with urllib.request.urlopen(req) as r:
        etag = r.headers["ETag"]
    done = call("POST", f"/files/{f['id']}/uploaded", {"id": f["upload"]["id"], "path": f["upload"]["path"],
        "parts": [{"number": 1, "checksum_etag": etag, "checksum_sha256_base64": sha}]})
    print("uploaded", done.get("id"), "is_uploaded:", done.get("is_uploaded"))
    return done["id"]

DESC = """**utask** syncs Apple Reminders, Google Tasks and Microsoft To Do in one fast terminal app (TUI + CLI + background daemon).

This download is the **ready-to-run macOS binary (Apple Silicon)**: no Python, no setup script. The source stays open on GitHub; you pay for the convenience, whatever it is worth to you.

- Full-screen TUI with themes (including your own terminal colors), global search, due dates, templates, undo
- Natural language add: `Call Anna @tomorrow`
- Background sync daemon, iCloud cross-device config, tokens in the macOS Keychain

Includes INSTALL.txt (3 commands). Docs: https://utask.sh"""

zip_path = sys.argv[1]
file_id = upload(zip_path)
benefit = call("POST", "/benefits/", {"type": "downloadables", "description": "utask 2.1.0 for macOS (Apple Silicon)", "properties": {"files": [file_id]}})
product = call("POST", "/products/", {"name": "uTask Standalone (macOS)", "description": DESC, "recurring_interval": None,
    "prices": [{"amount_type": "custom", "price_currency": "eur", "minimum_amount": 500, "preset_amount": 1200}]})
call("POST", f"/products/{product['id']}/benefits", {"benefits": [benefit["id"]]})
link = call("POST", "/checkout-links/", {"products": [product["id"]], "payment_processor": "stripe"})
print("product", product["id"]); print("checkout", link["url"])
