import asyncio
import os
import re
import random
from typing import Optional, List, Set
from datetime import datetime, timezone

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, ListView, ListItem, Label, Input, Static, Markdown, Sparkline, Tree
from textual.containers import Horizontal, Vertical, Container, ScrollableContainer
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen, ModalScreen

from sqlmodel import select, delete
from .core import AsyncSessionLocal, init_db
from .models import Task, TaskList

class HelpScreen(ModalScreen):
    """Displays the README.md content as a help manual."""
    # NO BINDINGS here - we use on_key for absolute capture

    def compose(self) -> ComposeResult:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        readme_path = os.path.join(base_dir, "README.md")
        content = "# 🛰️ utask v2.0 Manual\n\nREADME not found."
        if os.path.exists(readme_path):
            try:
                with open(readme_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    content = re.sub(r'([🎯🛠️🖥️💡⌨️⚡🔄🚀📱🛰️🔧📖✅◯❌⚠️•])([^\s])', r'\1 \2', content)
            except: pass
        
        with Vertical(id="help-dialog"):
            yield Label(" 📖   utask v2.0 - Documentation (ESC/Q to exit) ", id="help-header")
            with ScrollableContainer(id="help-scroll"):
                yield Markdown(content, id="help-markdown")

    def on_mount(self) -> None:
        # Focus the markdown so it can be scrolled immediately
        self.query_one("#help-markdown").focus()

    def on_key(self, event) -> None:
        # ABSOLUTE CAPTURE for exit keys
        if event.key in ("escape", "q"):
            event.stop()
            self.dismiss()

class TaskItem(ListItem):
    def __init__(self, task: Task):
        super().__init__()
        self.task_id = task.id
        self.task_title = task.title
        self.task_status = task.status
        self.priority = random.choice([0, 1, 2])

    def compose(self) -> ComposeResult:
        icon = "☐   " if self.task_status != "completed" else "☑   "
        prio_marker = ["", "!", "!!"][self.priority]
        prio_class = ["", "prio-med", "prio-high"][self.priority]
        content = f"{icon}{self.task_title}"
        if prio_marker:
            content = f"{icon}[{prio_class}]{prio_marker}[/] {self.task_title}"
        yield Label(content, classes="completed-task" if self.task_status == "completed" else "pending-task")

class UniversalTaskApp(App):
    CSS_PATH = "style.tcss"
    
    BINDINGS = [
        Binding("q", "quit", "Exit"), # NO priority=True
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("space", "toggle_complete", "Check"),
        Binding("v", "toggle_visual", "Visual"),
        Binding("d", "delete_task", "Delete"),
        Binding("u", "undo", "Undo"),
        Binding("a", "focus_add", "Add"),
        Binding("slash", "focus_search", "Search"),
        Binding("h", "toggle_completed_visibility", "Hide Done"),
        Binding("colon", "focus_command", "Command"),
        Binding(":", "focus_command", "Command", show=False),
        Binding("s", "sync_now", "Sync"),
        Binding("question_mark", "show_help", "Help"),
        Binding("escape", "cancel_input", "Cancel", show=False), # NO priority=True
    ]

    current_list = reactive("Reminders")
    show_completed = reactive(True)
    visual_mode = reactive(False)
    selected_ids: reactive[Set[int]] = reactive(set())
    undo_stack: List[tuple] = []
    is_syncing = reactive(False)

    def compose(self) -> ComposeResult:
        with Horizontal(id="header-stats"):
            yield Static("🚀 utask v2.0  •  ", id="header-title")
            yield Sparkline([random.randint(0, 10) for _ in range(20)], summary_function=max)
            yield Static("  •  [ 🟢 ONLINE ]", id="header-status")
        
        with Horizontal(id="app-grid"):
            with Vertical(id="sidebar"):
                yield Label(" 📂   LISTS ", classes="panel-header")
                yield Tree("📂 MY LISTS", id="list-tree")
            with Vertical(id="main-content"):
                yield Label(f" 📝   TASKS ({self.current_list}) ", id="task-list-header", classes="panel-header")
                yield Input(placeholder="Add Task... (Enter to save)", id="add-task-input", classes="hidden")
                yield ListView(id="task-list")
            with Vertical(id="details-panel"):
                yield Label(" ℹ️   DETAILS ", classes="panel-header")
                yield Static("Select a task...", id="details-content")
        
        with Container(id="command-container"):
            yield Label(":", id="command-prefix")
            yield Input(placeholder="Enter command...", id="command-input")
        
        yield Footer()

    async def on_mount(self) -> None:
        await init_db()
        await self.refresh_lists()
        tree = self.query_one("#list-tree", Tree)
        if tree.root.children:
            first_account = tree.root.children[0]
            if first_account.children:
                first_list = first_account.children[0]
                self.current_list = first_list.data
                tree.select_node(first_list)
        await self.refresh_tasks()
        self.set_timer(0.1, tree.focus)

    def watch_is_syncing(self, value: bool) -> None:
        for header in self.query("#header-status"):
            header.update("  •  [ 🟡 BUSY ]" if value else "  •  [ 🟢 ONLINE ]")

    async def refresh_lists(self) -> None:
        for tree in self.query("#list-tree"):
            tree.clear()
            tree.root.expand()
            async with AsyncSessionLocal() as session:
                statement = select(TaskList.name).distinct()
                result = await session.execute(statement)
                lists = result.scalars().all()
                groups = {}
                for full_name in sorted(lists):
                    if full_name.startswith("[") and "]" in full_name:
                        prefix, name = full_name.split("]", 1)
                        prefix = prefix[1:].strip()
                        name = name.strip()
                    else:
                        prefix, name = "Local", full_name
                    if prefix not in groups: groups[prefix] = []
                    groups[prefix].append((full_name, name))
                for prefix, items in groups.items():
                    node = tree.root.add(f"[bold mauve]{prefix}[/]", expand=True)
                    for full_name, short_name in items:
                        node.add_leaf(short_name, data=full_name)

    async def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if event.node.data:
            self.current_list = event.node.data
            await self.refresh_tasks()

    async def refresh_tasks(self) -> None:
        for view in self.query("#task-list"):
            view.clear()
            async with AsyncSessionLocal() as session:
                statement = select(Task).where(Task.list_name == self.current_list)
                if not self.show_completed:
                    statement = statement.where(Task.status != "completed")
                result = await session.execute(statement)
                tasks = result.scalars().all()
                tasks.sort(key=lambda t: (t.status == "completed", t.title.lower()))
                for t in tasks:
                    view.append(TaskItem(t))
            for header in self.query("#task-list-header"):
                header.update(f" 📝   TASKS ({self.current_list}) {'[HIDDEN DONE]' if not self.show_completed else ''} ")

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "task-list":
            await self.update_details(event.item.task_id)

    async def update_details(self, task_id: int) -> None:
        async with AsyncSessionLocal() as session:
            task = await session.get(Task, task_id)
            if task:
                content = (f"[bold][mauve]{task.title}[/][/]\n\n"
                           f"Status:   [mauve]{task.status}[/]\n"
                           f"List:     [mauve]{task.list_name}[/]\n"
                           f"Modified: [mauve]{task.last_modified.strftime('%Y-%m-%d %H:%M')}[/]\n"
                           f"Source:   [mauve]{task.source_provider or 'Local'}[/]\n\n"
                           f"--- Notes ---\n"
                           f"{task.description or '[Empty]'}")
                for detail in self.query("#details-content"):
                    detail.update(content)

    def action_focus_command(self) -> None:
        for container in self.query("#command-container"):
            container.add_class("visible")
        for cmd_input in self.query("#command-input"):
            cmd_input.value = ""
            cmd_input.focus()

    async def action_toggle_complete(self) -> None:
        for view in self.query("#task-list"):
            if view.index is not None:
                old_index = view.index
                item = view.children[view.index]
                async with AsyncSessionLocal() as session:
                    task = await session.get(Task, item.task_id)
                    if task:
                        task.status = "completed" if task.status != "completed" else "needsAction"
                        task.last_modified = datetime.now(timezone.utc)
                        session.add(task)
                        await session.commit()
                await self.refresh_tasks()
                view.index = min(old_index, len(view.children)-1) if view.children else None

    def action_toggle_visual(self) -> None:
        self.visual_mode = not self.visual_mode
        if not self.visual_mode: self.selected_ids = set()
        self.notify(f"Visual Mode: {'ON' if self.visual_mode else 'OFF'}")

    async def action_delete_task(self) -> None:
        for view in self.query("#task-list"):
            if view.index is not None:
                item = view.children[view.index]
                async with AsyncSessionLocal() as session:
                    task = await session.get(Task, item.task_id)
                    if task:
                        task_data = {c.name: getattr(task, c.name) for c in task.__table__.columns}
                        self.undo_stack.append(("delete", task_data))
                        await session.delete(task)
                        await session.commit()
                await self.refresh_tasks()

    async def action_undo(self) -> None:
        if not self.undo_stack:
            self.notify("Nothing to undo")
            return
        action, data = self.undo_stack.pop()
        if action == "delete":
            async with AsyncSessionLocal() as session:
                session.add(Task(**data))
                await session.commit()
            await self.refresh_tasks()
            self.notify("Restored task")

    def action_focus_add(self) -> None:
        for inp in self.query("#add-task-input"):
            inp.remove_class("hidden")
            inp.focus()

    def action_focus_search(self) -> None:
        self.action_focus_command()
        for cmd_input in self.query("#command-input"):
            cmd_input.value = "/"

    async def action_toggle_completed_visibility(self) -> None:
        self.show_completed = not self.show_completed
        await self.refresh_tasks()

    async def action_sync_now(self) -> None:
        self.is_syncing = True
        from .main import get_engine
        await get_engine().sync_all()
        self.is_syncing = False
        await self.refresh_lists()
        await self.refresh_tasks()
        self.notify("Sync completed")

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "command-input":
            raw_cmd = event.value.strip()
            cmd = raw_cmd.lower()
            for container in self.query("#command-container"):
                container.remove_class("visible")
            if cmd in ("q", "quit"): self.exit()
            elif cmd in ("help", "?"): self.push_screen(HelpScreen())
            elif cmd in ("h", "hide", "show"): await self.action_toggle_completed_visibility()
            elif cmd == "sync": await self.action_sync_now()
            elif cmd.startswith("delete list"):
                list_name = raw_cmd[11:].strip().strip('"').strip("'")
                if list_name: await self.action_delete_list(list_name)
                else: self.notify("Please specify a list name", severity="error")
        elif event.input.id == "add-task-input":
            title = event.value.strip()
            if title:
                async with AsyncSessionLocal() as session:
                    session.add(Task(title=title, list_name=self.current_list))
                    await session.commit()
                event.input.value = ""
                event.input.add_class("hidden")
                await self.refresh_tasks()
        for tree in self.query("#list-tree"): tree.focus()

    async def action_delete_list(self, list_name: str) -> None:
        self.notify(f"Deleting list '{list_name}' everywhere...", severity="warning")
        from .main import get_engine
        await get_engine().delete_list(list_name)
        if self.current_list == list_name: self.current_list = "Reminders"
        await self.refresh_lists()
        await self.refresh_tasks()
        self.notify(f"Deleted list: {list_name}")

    def action_cancel_input(self) -> None:
        for container in self.query("#command-container"): container.remove_class("visible")
        for inp in self.query("#add-task-input"): inp.add_class("hidden")
        for tree in self.query("#list-tree"): tree.focus()

    def action_cursor_down(self) -> None:
        for view in self.query("#task-list"):
            if view.index is not None and view.index < len(view.children) - 1:
                view.index += 1
                if self.visual_mode: self.selected_ids.add(view.children[view.index].task_id)

    def action_cursor_up(self) -> None:
        for view in self.query("#task-list"):
            if view.index is not None and view.index > 0:
                view.index -= 1
                if self.visual_mode: self.selected_ids.add(view.children[view.index].task_id)

if __name__ == "__main__":
    UniversalTaskApp().run()
