"""The setup assistant: see every account with its real state, add one, sign in again, remove one."""
import json
from pathlib import Path
from typing import Optional

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView, Select, Static

from . import accounts
from .config import CONFIG_DIR
from .security import load_secret
from .tui_text import escape

ICON = {accounts.OK: "[$success]●[/]", accounts.WARN: "[$warning]●[/]", accounts.BAD: "[$error]✖[/]"}
PROVIDERS = [("Apple Reminders", "apple"), ("Google Tasks", "google"), ("Microsoft To Do", "microsoft")]


class SetupScreen(ModalScreen):
    """Accounts overview. a add · r sign in again · d remove · esc close."""
    BINDINGS = [Binding("a", "add", "Add"), Binding("r", "reauth", "Sign in again"), Binding("d", "remove", "Remove"),
                Binding("escape", "close", "Close")]

    def __init__(self, welcome: bool = False):
        super().__init__()
        self.welcome = welcome
        self.changed = False
        self.state = {}  # (type, label) -> (state, text)

    def compose(self) -> ComposeResult:
        with Vertical(id="setup-dialog"):
            yield Label(" ACCOUNTS ", id="setup-header")
            yield Static("", id="setup-intro")
            yield ListView(id="setup-list")
            yield Static("", id="setup-detail")
            yield Label(" [b]a[/] add   [b]r[/] sign in again   [b]d[/] remove   [b]esc[/] close ", id="setup-footer")

    async def on_mount(self) -> None:
        intro = ("Welcome. utask keeps your tasks in one place and syncs them with the services below. "
                 "Connect an account to start, you can change this any time with [b]A[/].\n") if self.welcome else \
                "Every account with the state of its sign-in. [b]r[/] opens the login again, nothing else is touched."
        self.query_one("#setup-intro", Static).update(intro)
        await self.reload()

    async def reload(self) -> None:
        lv = self.query_one("#setup-list", ListView)
        await lv.clear()
        rows = accounts.list_accounts()
        if not rows:
            lv.append(ListItem(Label("[dim]No account yet. Press [b]a[/b] to add one.[/]"), disabled=True))
        for r in rows:
            item = ListItem(Label(f"[dim]…[/] {r['type'].capitalize():<10} {escape(r['label'])}", id=None))
            item.acct = (r["type"], r["label"])
            lv.append(item)
        if rows:
            lv.index = 0
            self.check_all([(r["type"], r["label"]) for r in rows])

    @work(thread=True, exclusive=True)
    def check_all(self, rows) -> None:
        for kind, label in rows:
            self.state[(kind, label)] = accounts.check_account(kind, label)
            self.app.call_from_thread(self.paint)

    def paint(self) -> None:
        lv = self.query_one("#setup-list", ListView)
        for item in lv.children:
            acct = getattr(item, "acct", None)
            if acct and acct in self.state:
                st, text = self.state[acct]
                item.query_one(Label).update(f"{ICON[st]} {acct[0].capitalize():<10} {escape(acct[1])}  [dim]{escape(text)}[/]")
        self.query_one("#setup-detail", Static).update("")

    def selected(self) -> Optional[tuple]:
        lv = self.query_one("#setup-list", ListView)
        if lv.index is None or lv.index >= len(lv.children):
            return None
        return getattr(lv.children[lv.index], "acct", None)

    def action_add(self) -> None:
        self.app.push_screen(AddAccountScreen(), self.after_add)

    def action_reauth(self) -> None:
        acct = self.selected()
        if acct:
            self.app.push_screen(AddAccountScreen(kind=acct[0], label=acct[1]), self.after_add)

    async def action_remove(self) -> None:
        acct = self.selected()
        if not acct:
            return
        accounts.remove_account(*acct)
        self.state.pop(acct, None)
        self.changed = True
        self.app.notify(f"Removed {acct[0]} {acct[1]}. Tasks already synced stay in the local database.")
        await self.reload()

    async def after_add(self, ok: Optional[bool]) -> None:
        if ok:
            self.changed = True
            await self.reload()

    def action_close(self) -> None:
        self.dismiss(self.changed)


class AddAccountScreen(ModalScreen):
    """Add an account or sign in again (kind and label given). Runs the real login and reports what happened."""
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, kind: Optional[str] = None, label: Optional[str] = None):
        super().__init__()
        self.kind, self.label, self.busy = kind, label, False

    def compose(self) -> ComposeResult:
        reauth = self.kind is not None
        with Vertical(id="add-dialog"):
            yield Label(" SIGN IN AGAIN " if reauth else " ADD ACCOUNT ", id="add-header")
            yield Select(PROVIDERS, value=self.kind or "google", allow_blank=False, id="add-kind", disabled=reauth)
            yield Input(value=self.label or "", placeholder="Name for this account, e.g. Private or Work", id="add-label", disabled=reauth)
            yield Input(placeholder="Google: path to your client_secret.json (or paste its content)", id="add-google-file")
            yield Input(placeholder="Microsoft: application (client) ID", id="add-ms-id")
            yield Input(placeholder="Microsoft: tenant (leave empty for 'common')", id="add-ms-tenant")
            yield Static("", id="add-status")
            with Horizontal(id="add-buttons"):
                yield Button("Authorize", id="add-go", variant="primary")
                yield Button("Cancel", id="add-cancel")

    def on_mount(self) -> None:
        guess = CONFIG_DIR / "client_secret.json"
        if guess.exists():
            self.query_one("#add-google-file", Input).value = str(guess)
        self.show_fields(self.kind or "google")
        self.query_one("#add-label" if not self.label else "#add-go").focus()

    def on_select_changed(self, event: Select.Changed) -> None:
        self.show_fields(str(event.value))

    def show_fields(self, kind: str) -> None:
        reauth = self.kind is not None
        self.query_one("#add-google-file").display = kind == "google" and not reauth
        self.query_one("#add-ms-id").display = kind == "microsoft" and not reauth
        self.query_one("#add-ms-tenant").display = kind == "microsoft" and not reauth
        hint = {"apple": "Apple Reminders needs no login: utask asks macOS for access.",
                "google": "Google opens your browser. The client file is the one from your own Google Cloud project (OAuth client of type Desktop app). Sign-in again reuses the saved client." if not reauth else "Google opens your browser to sign in again.",
                "microsoft": "Microsoft shows a code. Open the page it names and type the code. Needs the ID of an app you registered in Entra (public client)." if not reauth else "Microsoft shows a code to type on the page it names."}[kind]
        self.set_status(f"[dim]{hint}[/]")

    def set_status(self, text: str) -> None:
        self.query_one("#add-status", Static).update(text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-cancel":
            self.action_cancel()
        elif event.button.id == "add-go" and not self.busy:
            kind = self.kind or str(self.query_one("#add-kind", Select).value)
            label = (self.label or self.query_one("#add-label", Input).value).strip()
            if not label:
                self.set_status("[$error]Give the account a name first.[/]")
                return
            self.busy = True
            self.query_one("#add-go", Button).disabled = True
            self.set_status("[dim]Working …[/]")
            self.authorize(kind, label)

    @work(thread=True, exclusive=True)
    def authorize(self, kind: str, label: str) -> None:
        say = lambda t: self.app.call_from_thread(self.set_status, t)
        try:
            if kind == "apple":
                msg = accounts.apple_add(label)
            elif kind == "google":
                cfg = self.google_config(label)
                say("Browser opened: sign in to Google there. Waiting up to 4 minutes …")
                msg = accounts.google_authorize(label, cfg)
            else:
                client_id = load_secret("microsoft", "client_id", is_json=False, label=label) if self.kind else self.field("#add-ms-id")
                tenant = (load_secret("microsoft", "tenant_id", is_json=False, label=label) if self.kind else self.field("#add-ms-tenant")) or "common"
                if not client_id:
                    raise ValueError("Enter the Microsoft application (client) ID.")
                app, cache, flow = accounts.microsoft_begin(label, client_id, tenant)
                say(f"Open [b]{flow['verification_uri']}[/b] and type the code [b]{flow['user_code']}[/b]. Waiting …")
                msg = accounts.microsoft_finish(label, client_id, tenant, app, cache, flow)
            self.app.call_from_thread(self.done, True, msg)
        except Exception as e:
            self.app.call_from_thread(self.done, False, str(e))

    def field(self, selector: str) -> str:
        return self.app.call_from_thread(lambda: self.query_one(selector, Input).value.strip())

    def google_config(self, label: str) -> dict:
        if self.kind:  # signing in again: the saved token carries the client ID and secret
            saved = load_secret("google", "token", label=label)
            if isinstance(saved, dict) and saved.get("client_id") and saved.get("client_secret"):
                return accounts.google_client_config(client_id=saved["client_id"], client_secret=saved["client_secret"])
        return accounts.google_client_config(self.field("#add-google-file"))

    def done(self, ok: bool, msg: str) -> None:
        self.busy = False
        self.query_one("#add-go", Button).disabled = False
        if ok:
            self.app.notify(msg)
            self.dismiss(True)
        else:
            self.set_status(f"[$error]{escape(msg[:300])}[/]")

    def action_cancel(self) -> None:
        self.dismiss(False)
