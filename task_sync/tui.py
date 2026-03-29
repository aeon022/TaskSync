from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, ListView, ListItem, Label, Static, Input, MarkdownViewer, Tree
from textual.containers import Horizontal, Vertical, Container
from textual.binding import Binding
from textual.screen import ModalScreen
from sqlmodel import select
from .core import get_session, SyncEngine
from .models import Task, SyncMapping, TaskList
from .providers.apple import AppleRemindersProvider
import os
import threading
from functools import partial
import re

class HelpScreen(ModalScreen):
    """Ein modaler Bildschirm mit aggressivem Fokus-Highlight."""
    
    def compose(self) -> ComposeResult:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        readme_path = os.path.join(base_dir, "README.md")
        
        content = "# Hilfe\nREADME.md wurde nicht gefunden."
        if os.path.exists(readme_path):
            with open(readme_path, "r") as f:
                content = f.read()
        
        with Container(id="help-outer"):
            viewer = MarkdownViewer(content, show_table_of_contents=True)
            yield viewer
            yield Label("ESC/q: Schließen • TAB: Wechseln • j/k: Scrollen", id="help-footer")

    def on_mount(self) -> None:
        """Startet den Fokus-Check."""
        self.set_timer(0.1, self.force_focus_and_select)

    def force_focus_and_select(self) -> None:
        """Erzwingt Fokus auf den internen Baum und wählt den ersten Knoten."""
        try:
            viewer = self.query_one(MarkdownViewer)
            toc = viewer.query_one("MarkdownTableOfContents")
            # Wir suchen den echten Baum im TOC-Widget
            tree = toc.query_one(Tree)
            tree.focus()
            if tree.root.children:
                tree.select_node(tree.root.children[0])
                # Wir setzen zusätzlich den Cursor explizit
                tree.cursor_line = 0
        except:
            # Falls der Baum noch nicht geladen ist, in 100ms nochmal probieren
            self.set_timer(0.1, self.force_focus_and_select)

    def on_key(self, event) -> None:
        """Zentrale Steuerung für Navigation."""
        try:
            viewer = self.query_one(MarkdownViewer)
        except: return

        if event.key == "j":
            viewer.scroll_down()
            event.stop()
        elif event.key == "k":
            viewer.scroll_up()
            event.stop()
        elif event.key in ("pagedown", "page_down"):
            viewer.scroll_page_down()
            event.stop()
        elif event.key in ("pageup", "page_up"):
            viewer.scroll_page_up()
            event.stop()
        elif event.key in ("escape", "q"):
            self.app.pop_screen()
            event.stop()
        elif event.character == ":":
            self.app.pop_screen()

class TaskItem(ListItem):
    def __init__(self, task_id: int, title: str, status: str):
        super().__init__()
        self.task_id = task_id
        self.title = title
        self.status = status

    def compose(self) -> ComposeResult:
        icon = "✅" if self.status == "completed" else "⭕"
        text = f"{icon} {self.title}"
        if self.status == "completed":
            text = f"[strike]{text}[/strike]"
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
    
    #help-outer {
        align: center middle;
        padding: 2;
    }
    
    MarkdownViewer {
        background: $panel;
        border: thick $primary;
        height: 90%;
    }

    /* Das Inhaltsverzeichnis Container */
    MarkdownTableOfContents {
        border: thick $primary-background-darken-3;
        background: $panel;
    }

    /* UNÜBERSEHBARER RAHMEN wenn fokussiert */
    MarkdownTableOfContents:focus-within {
        border: thick $accent;
        background: $boost;
    }

    /* Den Baum selbst stylen */
    MarkdownTableOfContents > Tree {
        background: transparent;
        padding: 1;
    }

    /* Das Highlight des gewählten Eintrags verstärken */
    MarkdownTableOfContents > Tree:focus > .tree--cursor {
        background: $accent;
        color: $text;
        text-style: bold;
    }

    #help-footer {
        text-align: center;
        background: $primary;
        color: white;
        width: 100%;
        padding: 1;
    }
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
        self.search_filter = ""
        self.sort_method = "status"

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("[b]Listen[/b]")
                yield ListView(id="list-selector")
            with Vertical(id="main-content"):
                yield Label(f"[b]Aufgaben in {self.current_list}[/b]", id="list-title")
                yield Input(placeholder="Neue Aufgabe...", id="add-task-input")
                yield Input(placeholder="Suchen...", id="search-input")
                yield Input(placeholder="Umbenennen...", id="rename-input")
                yield ListView(id="task-list")
        yield Input(id="command-bar", placeholder=":")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_lists()
        self.refresh_tasks()
        try:
            self.query_one("#task-list").focus()
        except: pass
        self.run_worker(self.bg_load_lists, thread=True)

    def refresh_lists(self) -> None:
        try:
            sidebar = self.query_one("#list-selector", ListView)
            sidebar.clear()
            with get_session() as session:
                lists = session.exec(select(TaskList)).all()
                if not lists:
                    sidebar.append(ListItem(Label("Reminders")))
                else:
                    for l in sorted(lists, key=lambda x: x.name):
                        sidebar.append(ListItem(Label(l.name)))
                        if l.name == self.current_list:
                            sidebar.index = len(sidebar) - 1
        except: pass

    def bg_load_lists(self):
        try:
            real_lists = self.providers[0].get_lists()
            if not real_lists: return
            unique_names = list(set(real_lists))
            with get_session() as session:
                session.execute("DELETE FROM tasklist")
                for name in unique_names:
                    session.add(TaskList(name=name, provider_name="apple"))
                session.commit()
            self.call_from_thread(self.refresh_lists)
        except: pass

    def action_add_task(self) -> None:
        add_input = self.query_one("#add-task-input", Input)
        add_input.display = True
        add_input.focus()

    def action_rename_task(self) -> None:
        task_list = self.query_one("#task-list", ListView)
        if task_list.index is not None:
            item = task_list.children[task_list.index]
            if isinstance(item, TaskItem):
                rename_input = self.query_one("#rename-input", Input)
                rename_input.display = True
                rename_input.value = item.title
                rename_input.focus()
                rename_input.cursor_position = len(item.title)

    def action_focus_search(self) -> None:
        search_input = self.query_one("#search-input", Input)
        search_input.display = True
        search_input.focus()

    def action_focus_command_bar(self) -> None:
        command_bar = self.query_one("#command-bar", Input)
        footer = self.query_one(Footer)
        footer.display = False
        command_bar.display = True
        command_bar.value = ":"
        command_bar.focus()
        command_bar.cursor_position = 1

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self.search_filter = event.value.strip().lower()
            self.refresh_tasks()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        input_widget = event.input
        value = event.value.strip()
        input_widget.display = False
        input_widget.value = ""
        self.query_one("#task-list").focus()
        if input_widget.id == "command-bar":
            self.query_one(Footer).display = True
            if value.startswith(":"):
                self.handle_command(value[1:])
        elif input_widget.id == "rename-input":
            task_list = self.query_one("#task-list", ListView)
            if value and task_list.index is not None:
                item = task_list.children[task_list.index]
                if isinstance(item, TaskItem):
                    with get_session() as session:
                        task = session.get(Task, item.task_id)
                        if task:
                            task.title = value
                            session.add(task)
                            session.commit()
                    self.refresh_tasks()
                    self.run_worker(partial(self.bg_sync_rename, item.task_id, value, self.current_list), thread=True)
        elif input_widget.id == "add-task-input":
            if value:
                with get_session() as session:
                    new_task = Task(title=value)
                    session.add(new_task)
                    session.commit()
                    session.refresh(new_task)
                    task_id = new_task.id
                self.refresh_tasks()
                self.run_worker(partial(self.bg_sync_add, task_id, value, self.current_list), thread=True)

    def bg_sync_add(self, task_id: int, title: str, list_name: str):
        try:
            provider = AppleRemindersProvider(list_name=list_name)
            with get_session() as session:
                task = session.get(Task, task_id)
                if task:
                    remote_id = provider.create_task(task)
                    if remote_id:
                        mapping = SyncMapping(task_id=task_id, provider_name=provider.name, remote_id=remote_id)
                        session.add(mapping)
                        session.commit()
        except: pass

    def bg_sync_rename(self, task_id: int, new_title: str, list_name: str):
        try:
            provider = AppleRemindersProvider(list_name=list_name)
            with get_session() as session:
                task = session.get(Task, task_id)
                if task:
                    mappings = session.exec(select(SyncMapping).where(SyncMapping.task_id == task_id)).all()
                    for mapping in mappings:
                        provider.update_task(mapping.remote_id, task)
        except: pass

    def bg_sync_status(self, task_id: int, list_name: str):
        try:
            provider = AppleRemindersProvider(list_name=list_name)
            with get_session() as session:
                task = session.get(Task, task_id)
                if task:
                    mappings = session.exec(select(SyncMapping).where(SyncMapping.task_id == task_id)).all()
                    for mapping in mappings:
                        provider.update_task(mapping.remote_id, task)
        except: pass

    def bg_sync_delete(self, task_id: int, list_name: str):
        try:
            provider = AppleRemindersProvider(list_name=list_name)
            with get_session() as session:
                mapping = session.exec(select(SyncMapping).where(SyncMapping.task_id == task_id)).first()
                if mapping:
                    provider.delete_task(mapping.remote_id)
                    session.delete(mapping)
                    session.commit()
        except: pass

    def on_key(self, event) -> None:
        inputs = self.query(Input)
        visible_input = next((inp for inp in inputs if inp.display), None)
        if visible_input:
            if event.key == "escape":
                for inp in inputs:
                    inp.display = False
                    inp.value = ""
                self.query_one(Footer).display = True
                self.query_one("#task-list").focus()
                if visible_input.id == "search-input":
                    self.search_filter = ""
                    self.refresh_tasks()
                event.prevent_default(); event.stop()
            return
        if event.character == ":" or event.key == "colon":
            self.action_focus_command_bar(); event.prevent_default(); event.stop()
        elif event.character == "/":
            self.action_focus_search(); event.prevent_default(); event.stop()
        elif event.key == "r":
            self.action_rename_task(); event.prevent_default(); event.stop()

    def handle_command(self, cmd: str) -> None:
        import re
        if cmd in ("q", "quit"): self.exit(); return
        if cmd in ("help", "readme", "open help", "open readme"):
            self.push_screen(HelpScreen()); return
        sort_match = re.match(r'sort\s+(alpha|date|status)', cmd)
        if sort_match:
            self.sort_method = sort_match.group(1)
            self.notify(f"Sortierung: {self.sort_method}")
            self.refresh_tasks(); return
        create_match = re.match(r'create list\s+"([^"]+)"', cmd)
        if create_match:
            name = create_match.group(1)
            def do_create():
                if self.providers[0].create_list(name):
                    self.notify(f"Liste erstellt: {name}")
                    self.run_worker(self.bg_load_lists, thread=True)
                else: self.notify(f"Fehler: {name}", severity="error")
            self.run_worker(do_create, thread=True); return
        delete_match = re.match(r'delete list\s+"([^"]+)"', cmd)
        if delete_match:
            name = delete_match.group(1)
            def do_delete():
                if self.providers[0].delete_list(name):
                    self.notify(f"Liste gelöscht: {name}")
                    if self.current_list == name: self.current_list = "Reminders"
                    self.run_worker(self.bg_load_lists, thread=True)
                    self.call_from_thread(self.refresh_tasks)
                else: self.notify(f"Fehler: {name}", severity="error")
            self.run_worker(do_delete, thread=True); return
        self.notify(f"Unbekannt: {cmd}", severity="error")

    def refresh_tasks(self) -> None:
        try:
            task_list_view = self.query_one("#task-list", ListView)
            task_list_view.clear()
            with get_session() as session:
                tasks = session.exec(select(Task)).all()
                if self.search_filter:
                    tasks = [t for t in tasks if self.search_filter in t.title.lower()]
                if self.sort_method == "alpha":
                    tasks.sort(key=lambda t: t.title.lower())
                elif self.sort_method == "status":
                    tasks.sort(key=lambda t: (t.status != "needsAction", t.title.lower()))
                for task in tasks:
                    task_list_view.append(TaskItem(task.id, task.title, task.status))
        except: pass

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "list-selector":
            self.current_list = str(event.item.query_one(Label).renderable)
            self.query_one("#list-title", Label).update(f"[b]Aufgaben in {self.current_list}[/b]")
            self.refresh_tasks()

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
                task_id = item.task_id
                self.run_worker(partial(self.bg_sync_delete, task_id, self.current_list), thread=True)
                with get_session() as session:
                    task = session.get(Task, task_id)
                    if task:
                        session.delete(task); session.commit()
                self.refresh_tasks()

    def action_sync(self) -> None:
        self.notify("Synchronisiere...")
        def do_sync():
            engine = SyncEngine(self.providers)
            engine.sync()
            self.call_from_thread(self.refresh_tasks)
            self.notify("Sync abgeschlossen!")
        self.run_worker(do_sync, thread=True)

if __name__ == "__main__":
    app = UniversalTaskApp()
    app.run()
