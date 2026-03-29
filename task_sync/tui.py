from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, ListView, ListItem, Label, Static, Input, MarkdownViewer, Tree, TextArea
from textual.containers import Horizontal, Vertical, Container
from textual.binding import Binding
from textual.screen import ModalScreen
from sqlmodel import select
from .core import get_session, SyncEngine
from .models import Task, SyncMapping, TaskList
from .providers.apple import AppleRemindersProvider
from .providers.google import GoogleTasksProvider
from .providers.microsoft import MicrosoftToDoProvider
import os
import threading
from functools import partial
import json
import re
from pathlib import Path

class MicrosoftSetupScreen(ModalScreen):
    """Assistent für Microsoft To Do Einrichtung."""
    def compose(self) -> ComposeResult:
        with Container(id="setup-container"):
            yield Label("[b]Microsoft To Do Einrichtung[/b]", id="setup-title")
            yield Label("1. Azure Portal öffnen (siehe Hilfe :help)")
            yield Label("2. 'Application (client) ID' kopieren.")
            yield Input(placeholder="Application (client) ID", id="ms-client-id")
            yield Label("Drücke ENTER zum Speichern & Login starten • ESC zum Abbrechen")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        client_id = self.query_one("#ms-client-id", Input).value.strip()
        if client_id:
            ms = MicrosoftToDoProvider()
            ms.save_app_credentials(client_id)
            self.app.notify("Microsoft ID gespeichert!")
            self.app.pop_screen()
            self.app.handle_command("auth microsoft")
        else:
            self.app.notify("Bitte Client ID eingeben.", severity="error")

    def on_key(self, event) -> None:
        if event.key == "escape": self.app.pop_screen()

class GoogleSetupScreen(ModalScreen):
    """Ein Assistent, der die credentials.json automatisch für den Nutzer anlegt."""
    def compose(self) -> ComposeResult:
        with Container(id="setup-container"):
            yield Label("[b]Google Cloud Identität einfügen[/b]", id="setup-title")
            yield Label("1. JSON-Inhalt von Google Cloud Console kopieren.")
            yield Label("2. Hier einfügen (CMD+V):")
            yield TextArea(id="creds-input")
            yield Label("Drücke STRG+S zum Speichern & Browser-Login starten.", id="setup-hint")

    def on_key(self, event) -> None:
        if event.key == "escape": self.app.pop_screen()
        if event.key == "ctrl+s":
            raw_json = self.query_one("#creds-input", TextArea).text.strip()
            try:
                parsed = json.loads(raw_json)
                config_dir = Path.home() / ".config" / "utask"
                os.makedirs(config_dir, exist_ok=True)
                with open(config_dir / "credentials.json", "w") as f: json.dump(parsed, f)
                self.app.notify("Identität gespeichert! Starte Browser...")
                self.app.pop_screen(); self.app.handle_command("auth google")
            except: self.app.notify("Fehler: Ungültiges JSON-Format!", severity="error")

class HelpScreen(ModalScreen):
    """Ein modaler Bildschirm mit sofortigem Fokus-Highlight."""
    def compose(self) -> ComposeResult:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        readme_path = os.path.join(base_dir, "README.md")
        content = "# Hilfe\nREADME.md wurde nicht gefunden."
        if os.path.exists(readme_path):
            with open(readme_path, "r") as f: content = f.read()
        with Container(id="help-outer"):
            viewer = MarkdownViewer(content, show_table_of_contents=True)
            yield viewer
            yield Label("ESC/q: Schließen • TAB: Wechseln • j/k: Scrollen", id="help-footer")

    def on_mount(self) -> None: self.set_timer(0.1, self.force_focus_and_select)

    def force_focus_and_select(self) -> None:
        try:
            viewer = self.query_one(MarkdownViewer); toc = viewer.query_one("MarkdownTableOfContents")
            tree = toc.query_one(Tree); tree.focus()
            if tree.root.children: tree.select_node(tree.root.children[0]); tree.cursor_line = 0
        except: self.set_timer(0.1, self.force_focus_and_select)

    def on_key(self, event) -> None:
        try: viewer = self.query_one(MarkdownViewer)
        except: return
        if event.key == "j": viewer.scroll_down(); event.stop()
        elif event.key == "k": viewer.scroll_up(); event.stop()
        elif event.key in ("pagedown", "page_down"): viewer.scroll_page_down(); event.stop()
        elif event.key in ("pageup", "page_up"): viewer.scroll_page_up(); event.stop()
        elif event.key in ("escape", "q"): self.app.pop_screen(); event.stop()
        elif event.character == ":": self.app.pop_screen()

class TaskItem(ListItem):
    def __init__(self, task_id: int, title: str, status: str):
        super().__init__()
        self.task_id = task_id; self.title = title; self.status = status
    def compose(self) -> ComposeResult:
        icon = "✅" if self.status == "completed" else "⭕"
        text = f"{icon} {self.title}"
        if self.status == "completed": text = f"[strike]{text}[/strike]"
        yield Label(text)

class UniversalTaskApp(App):
    CSS = """
    Screen { layout: horizontal; }
    #sidebar { width: 30%; background: $primary-background-darken-1; border-right: solid $primary; }
    #main-content { width: 70%; }
    .completed { text-style: strike; color: $text-muted; }
    #add-task-input, #search-input, #rename-input { display: none; dock: top; }
    #command-bar { display: none; dock: bottom; height: 1; border: none; background: #000000; color: #ffffff; text-style: bold; }
    Footer { background: $primary; }
    #help-outer { align: center middle; padding: 2; }
    MarkdownViewer { background: $panel; border: thick $primary; height: 90%; }
    MarkdownTableOfContents { border: thick $primary-background-darken-3; background: $panel; }
    MarkdownTableOfContents:focus-within { border: thick $accent; background: $boost; }
    MarkdownTableOfContents > Tree { background: transparent; padding: 1; }
    MarkdownTableOfContents > Tree:focus > .tree--cursor { background: $accent; color: $text; text-style: bold; }
    #help-footer { text-align: center; background: $primary; color: white; width: 100%; padding: 1; }
    
    #setup-container {
        width: 80%; height: 80%; background: $panel; border: thick $primary; align: center middle; padding: 1;
    }
    #setup-title { background: $primary; color: white; width: 100%; text-align: center; margin-bottom: 1; padding: 1; }
    #creds-input { height: 1fr; margin: 1 0; border: solid $primary; }
    #setup-container > Input { margin: 1 0; border: solid $primary; }
    #setup-hint { text-align: center; color: $text-muted; }
    """

    BINDINGS = [
        Binding("q", "quit", "Beenden", show=True),
        Binding("j", "cursor_down", "Runter", show=False),
        Binding("k", "cursor_up", "Hoch", show=False),
        Binding("space", "toggle_complete", "Erledigen", show=True),
        Binding("a", "add_task", "Neu", show=True),
        Binding("d", "delete_task", "Löschen", show=True),
        Binding("s", "sync", "Sync", show=True),
        Binding(":", "focus_command_bar", "Befehl", show=False),
        Binding("colon", "focus_command_bar", "Befehl", show=False),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_list = "Reminders"
        self.providers = [AppleRemindersProvider(list_name="Reminders")]
        g = GoogleTasksProvider(); ms = MicrosoftToDoProvider()
        if g.is_authenticated(): self.providers.append(g)
        if ms.is_authenticated(): self.providers.append(ms)
        self.search_filter = ""; self.sort_method = "status"

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("[b]Listen[/b]"); yield ListView(id="list-selector")
            with Vertical(id="main-content"):
                yield Label(f"[b]Aufgaben in {self.current_list}[/b]", id="list-title")
                yield Input(placeholder="Neue Aufgabe...", id="add-task-input")
                yield Input(placeholder="Suchen...", id="search-input")
                yield Input(placeholder="Umbenennen...", id="rename-input")
                yield ListView(id="task-list")
        yield Input(id="command-bar", placeholder=":")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_lists(); self.refresh_tasks()
        try: self.query_one("#task-list").focus()
        except: pass
        self.run_worker(self.bg_load_lists, thread=True)

    def refresh_lists(self) -> None:
        try:
            sidebar = self.query_one("#list-selector", ListView); sidebar.clear()
            with get_session() as session:
                lists = session.exec(select(TaskList)).all()
                if not lists: sidebar.append(ListItem(Label("Reminders")))
                else:
                    for l in sorted(lists, key=lambda x: x.name):
                        sidebar.append(ListItem(Label(l.name)))
                        if l.name == self.current_list: sidebar.index = len(sidebar) - 1
        except: pass

    def bg_load_lists(self):
        try:
            real_lists = []
            for p in self.providers: real_lists.extend(p.get_lists())
            if not real_lists: return
            unique_names = list(set(real_lists))
            with get_session() as session:
                session.execute("DELETE FROM tasklist")
                for name in unique_names: session.add(TaskList(name=name, provider_name="sync"))
                session.commit()
            self.call_from_thread(self.refresh_lists)
        except: pass

    def action_add_task(self) -> None:
        add_input = self.query_one("#add-task-input", Input); add_input.display = True; add_input.focus()

    def action_rename_task(self) -> None:
        task_list = self.query_one("#task-list", ListView)
        if task_list.index is not None:
            item = task_list.children[task_list.index]
            if isinstance(item, TaskItem):
                rename_input = self.query_one("#rename-input", Input)
                rename_input.display = True; rename_input.value = item.title; rename_input.focus()
                rename_input.cursor_position = len(item.title)

    def action_focus_search(self) -> None:
        search_input = self.query_one("#search-input", Input); search_input.display = True; search_input.focus()

    def action_focus_command_bar(self) -> None:
        command_bar = self.query_one("#command-bar", Input); footer = self.query_one(Footer)
        footer.display = False; command_bar.display = True; command_bar.value = ":"; command_bar.focus()
        command_bar.cursor_position = 1

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input": self.search_filter = event.value.strip().lower(); self.refresh_tasks()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        input_widget = event.input; value = event.value.strip()
        input_widget.display = False; input_widget.value = ""; self.query_one("#task-list").focus()
        if input_widget.id == "command-bar":
            self.query_one(Footer).display = True
            if value.startswith(":"): self.handle_command(value[1:])
        elif input_widget.id == "rename-input":
            task_list = self.query_one("#task-list", ListView)
            if value and task_list.index is not None:
                item = task_list.children[task_list.index]
                if isinstance(item, TaskItem):
                    with get_session() as session:
                        task = session.get(Task, item.task_id)
                        if task: task.title = value; session.add(task); session.commit()
                    self.refresh_tasks()
                    self.run_worker(partial(self.bg_sync_rename, item.task_id, value, self.current_list), thread=True)
        elif input_widget.id == "add-task-input":
            if value:
                with get_session() as session:
                    new_task = Task(title=value, list_name=self.current_list)
                    session.add(new_task); session.commit()
                    session.refresh(new_task); task_id = new_task.id
                self.refresh_tasks()
                self.run_worker(partial(self.bg_sync_add, task_id, value, self.current_list), thread=True)

    def bg_sync_add(self, task_id: int, title: str, list_name: str):
        try:
            with get_session() as session:
                task = session.get(Task, task_id)
                if task:
                    for p in self.providers:
                        remote_id = p.create_task(task)
                        if remote_id: session.add(SyncMapping(task_id=task_id, provider_name=p.name, remote_id=remote_id))
                    session.commit()
        except: pass

    def bg_sync_rename(self, task_id: int, new_title: str, list_name: str):
        try:
            with get_session() as session:
                task = session.get(Task, task_id)
                if task:
                    mappings = session.exec(select(SyncMapping).where(SyncMapping.task_id == task_id)).all()
                    for m in mappings:
                        for p in self.providers:
                            if p.name == m.provider_name: p.update_task(m.remote_id, task)
        except: pass

    def bg_sync_status(self, task_id: int, list_name: str):
        try:
            with get_session() as session:
                task = session.get(Task, task_id)
                if task:
                    mappings = session.exec(select(SyncMapping).where(SyncMapping.task_id == task_id)).all()
                    for m in mappings:
                        for p in self.providers:
                            if p.name == m.provider_name: p.update_task(m.remote_id, task)
        except: pass

    def bg_sync_delete(self, task_id: int, list_name: str):
        try:
            with get_session() as session:
                mappings = session.exec(select(SyncMapping).where(SyncMapping.task_id == task_id)).all()
                for m in mappings:
                    for p in self.providers:
                        if p.name == m.provider_name: p.delete_task(m.remote_id)
                    session.delete(m)
                session.commit()
        except: pass

    def on_key(self, event) -> None:
        try:
            inputs = self.query(Input); visible_input = next((inp for inp in inputs if inp.display), None)
        except: return
        if visible_input:
            if event.key == "escape":
                for inp in inputs: inp.display = False; inp.value = ""
                self.query_one(Footer).display = True; self.query_one("#task-list").focus()
                if visible_input.id == "search-input": self.search_filter = ""; self.refresh_tasks()
                event.prevent_default(); event.stop()
            return
        if event.character == ":" or event.key == "colon": self.action_focus_command_bar(); event.prevent_default(); event.stop()
        elif event.character == "/": self.action_focus_search(); event.prevent_default(); event.stop()
        elif event.key == "r": self.action_rename_task(); event.prevent_default(); event.stop()

    def handle_command(self, cmd: str) -> None:
        import re
        if cmd in ("q", "quit"): self.exit(); return
        if cmd in ("help", "readme", "open help", "open readme"): self.push_screen(HelpScreen()); return
        if cmd == "auth google":
            g = GoogleTasksProvider()
            if g.run_login_flow() == "MISSING_FILE":
                self.push_screen(GoogleSetupScreen())
                return
            
            def do_auth():
                if g.run_login_flow() == "SUCCESS":
                    self.notify("Google verbunden!")
                    self.providers.append(g)
                    self.run_worker(self.bg_load_lists, thread=True)
                else:
                    self.notify("Login fehlgeschlagen.", severity="error")
            self.run_worker(do_auth, thread=True)
            return
        if cmd == "auth microsoft":
            ms = MicrosoftToDoProvider()
            if not ms.has_app_credentials():
                self.push_screen(MicrosoftSetupScreen())
                return
            def do_auth_ms():
                res = ms.run_login_flow()
                if isinstance(res, dict):
                    self.notify(f"Code: {res['code']} - Browser wird geöffnet...")
                    import webbrowser; webbrowser.open(res['url'])
                    if ms.complete_login(res['flow'], res['app']) == "SUCCESS":
                        self.notify("Microsoft verbunden!")
                        self.providers.append(ms)
                        self.run_worker(self.bg_load_lists, thread=True)
                    else:
                        self.notify("Microsoft Login fehlgeschlagen.", severity="error")
            self.run_worker(do_auth_ms, thread=True)
            return
        sort_match = re.match(r'sort\s+(alpha|date|status)', cmd)
        if sort_match:
            self.sort_method = sort_match.group(1)
            self.notify(f"Sortierung: {self.sort_method}")
            self.refresh_tasks()
            return
        create_match = re.match(r'create list\s+"([^"]+)"', cmd)
        if create_match:
            name = create_match.group(1)
            def do_create():
                for p in self.providers: p.create_list(name)
                self.notify(f"Liste erstellt: {name}")
                self.run_worker(self.bg_load_lists, thread=True)
            self.run_worker(do_create, thread=True)
            return
        delete_match = re.match(r'delete list\s+"([^"]+)"', cmd)
        if delete_match:
            name = delete_match.group(1)
            def do_delete():
                self.notify(f"Liste gelöscht: {name}")
                self.run_worker(self.bg_load_lists, thread=True)
            self.run_worker(do_delete, thread=True)
            return
        self.notify(f"Unbekannt: {cmd}", severity="error")

    def refresh_tasks(self) -> None:
        try:
            task_list_view = self.query_one("#task-list", ListView); task_list_view.clear()
            with get_session() as session:
                # Filter by current_list
                tasks = session.exec(select(Task).where(Task.list_name == self.current_list)).all()
                if self.search_filter: tasks = [t for t in tasks if self.search_filter in t.title.lower()]
                if self.sort_method == "alpha": tasks.sort(key=lambda t: t.title.lower())
                elif self.sort_method == "status": tasks.sort(key=lambda t: (t.status != "needsAction", t.title.lower()))
                for task in tasks: task_list_view.append(TaskItem(task.id, task.title, task.status))
        except: pass

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "list-selector":
            self.current_list = str(event.item.query_one(Label).renderable)
            self.query_one("#list-title", Label).update(f"[b]Aufgaben in {self.current_list}[/b]"); self.refresh_tasks()

    def action_toggle_complete(self) -> None:
        task_list = self.query_one("#task-list", ListView)
        if task_list.index is not None:
            item = task_list.children[task_list.index]
            if isinstance(item, TaskItem):
                with get_session() as session:
                    task = session.get(Task, item.task_id)
                    if task:
                        task.status = "completed" if task.status == "needsAction" else "needsAction"
                        session.add(task); session.commit()
                        self.run_worker(partial(self.bg_sync_status, task.id, self.current_list), thread=True)
                self.refresh_tasks()

    def action_delete_task(self) -> None:
        task_list = self.query_one("#task-list", ListView)
        if task_list.index is not None:
            item = task_list.children[task_list.index]
            if isinstance(item, TaskItem):
                task_id = item.task_id; self.run_worker(partial(self.bg_sync_delete, task_id, self.current_list), thread=True)
                with get_session() as session:
                    task = session.get(Task, task_id)
                    if task: session.delete(task); session.commit()
                self.refresh_tasks()

    def action_sync(self) -> None:
        self.notify("Synchronisiere...")
        def do_sync():
            engine = SyncEngine(self.providers); engine.sync()
            self.call_from_thread(self.refresh_tasks); self.notify("Sync abgeschlossen!")
        self.run_worker(do_sync, thread=True)

if __name__ == "__main__":
    app = UniversalTaskApp(); app.run()
