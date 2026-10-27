"""Accounts and the setup assistant against an in-memory Keychain and a throwaway home folder.
Run: .venv/bin/python tests/test_accounts.py"""
import asyncio, json, os, sys, tempfile
HOME = tempfile.mkdtemp(); os.environ["HOME"] = HOME   # before any utask import: the config folder is derived from it
import keyring
from keyring.backend import KeyringBackend

class Mem(KeyringBackend):
    priority = 9
    def __init__(s): s.d = {}
    def get_password(s, a, b): return s.d.get((a, b))
    def set_password(s, a, b, c): s.d[(a, b)] = c
    def delete_password(s, a, b):
        if (a, b) not in s.d: raise keyring.errors.PasswordDeleteError("missing")
        del s.d[(a, b)]
mem = Mem(); keyring.set_keyring(mem)

from task_sync import accounts
from task_sync.config import add_provider_config, load_provider_config
from task_sync.security import load_secret, save_secret

# 1. migration: one legacy token, two Google accounts -> it goes to the first only, never to both
add_provider_config("google", "Private"); add_provider_config("google", "Work"); add_provider_config("microsoft", "FH")
save_secret("google", "token", {"client_id": "cid", "client_secret": "sec", "refresh_token": "legacy"})
save_secret("microsoft", "client_id", "ms-id", ); save_secret("microsoft", "tenant_id", "common")
moved = accounts.migrate_legacy_secrets()
assert "google/Private/token" in moved and not any("Work" in m for m in moved), moved
assert load_secret("google", "token", label="Private")["refresh_token"] == "legacy"
assert load_secret("google", "token", label="Work") is None
assert load_secret("microsoft", "client_id", is_json=False, label="FH") == "ms-id"
assert accounts.migrate_legacy_secrets() == [], "migration must be idempotent"

# 2. Google sign-in stores a token per label; two accounts never share one
class FakeCreds:
    def __init__(s, n): s.n = n
    def to_json(s): return json.dumps({"client_id": "c", "client_secret": "s", "refresh_token": s.n})
class FakeFlow:
    n = 0
    @classmethod
    def from_client_config(cls, cfg, scopes): return cls()
    def run_local_server(self, **kw):
        FakeFlow.n += 1; return FakeCreds(f"token{FakeFlow.n}")
import google_auth_oauthlib.flow as gflow
gflow.InstalledAppFlow = FakeFlow
cfg = accounts.google_client_config(client_id="c", client_secret="s")
accounts.google_authorize("Home", cfg); accounts.google_authorize("Office", cfg)
assert load_secret("google", "token", label="Home")["refresh_token"] == "token1"
assert load_secret("google", "token", label="Office")["refresh_token"] == "token2"
assert {"type": "google", "label": "Home"} in load_provider_config()
for bad in ("", "{}", '{"nope": 1}'):
    try: accounts.google_client_config(bad); raise SystemExit(f"accepted {bad!r}")
    except ValueError: pass

# 3. Microsoft sign-in keeps the token cache (a new process starts signed in)
import msal
class FakeApp:
    def __init__(s, cid, authority=None, token_cache=None): s.cache = token_cache
    def initiate_device_flow(s, scopes): return {"user_code": "ABC-123", "verification_uri": "https://microsoft.com/devicelogin"}
    def acquire_token_by_device_flow(s, flow):
        s.cache.deserialize(json.dumps({"RefreshToken": {"x": {"secret": "r"}}})); return {"access_token": "t"}
msal.PublicClientApplication = FakeApp
app, cache, flow = accounts.microsoft_begin("Work365", "ms-id2", "tenant")
assert flow["user_code"] == "ABC-123"
accounts.microsoft_finish("Work365", "ms-id2", "tenant", app, cache, flow)
assert "RefreshToken" in load_secret("microsoft", "cache", is_json=False, label="Work365")
assert load_secret("microsoft", "client_id", is_json=False, label="Work365") == "ms-id2"
from task_sync.providers.microsoft import MicrosoftToDoProvider
assert MicrosoftToDoProvider("Work365").cache.serialize().find("RefreshToken") >= 0, "provider does not load the saved cache"

# 4. a revoked token is reported as such, and remove forgets everything
from task_sync.providers import google as gp
class DeadCreds:
    expired = True; refresh_token = "r"
    def refresh(self, req): raise Exception("invalid_grant: Bad Request")
    def to_json(self): return "{}"
orig = gp.GoogleTasksProvider._load_creds
gp.GoogleTasksProvider._load_creds = lambda self: DeadCreds()
orig_build = gp.build; gp.build = lambda *a, **k: None
state, text = accounts.check_account("google", "Home")
gp.GoogleTasksProvider._load_creds = orig; gp.build = orig_build
assert state == accounts.BAD and "sign in again" in text, (state, text)
accounts.remove_account("google", "Home")
assert load_secret("google", "token", label="Home") is None and {"type": "google", "label": "Home"} not in load_provider_config()

# 5. the assistant: add a Microsoft account end to end through the interface
from task_sync.tui import UniversalTaskApp
async def ui():
    app = UniversalTaskApp()
    async with app.run_test(size=(110, 36)) as pilot:
        await pilot.pause(1.5)
        await pilot.press("A"); await pilot.pause(1.5)
        listed = [getattr(i, "acct", None) for i in app.screen.query("ListItem")]
        assert ("google", "Private") in listed and ("microsoft", "Work365") in listed, listed
        await pilot.press("a"); await pilot.pause(0.5)
        scr = app.screen
        scr.query_one("#add-kind").value = "microsoft"; await pilot.pause(0.3)
        scr.query_one("#add-label").value = "Fresh"
        scr.query_one("#add-ms-id").value = "ms-fresh"
        await pilot.click("#add-go"); await pilot.pause(2.0)
        assert ("microsoft", "Fresh") in [(p["type"], p["label"]) for p in load_provider_config()], load_provider_config()
        assert load_secret("microsoft", "cache", is_json=False, label="Fresh")
asyncio.run(ui())
print("ok")
