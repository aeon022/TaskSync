import asyncio
import os
import re
import random
import subprocess
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
        self.query_one("#help-markdown").focus()

    def on_key(self, event) -> None:
        if event.key in ("escape", "q"):
            event.stop()
            self.dismiss()

class FocusScreen(ModalScreen):
    """Pomodoro Focus Mode Screen."""
    def __init__(self, task_id: int, task_title: str):
        super().__init__()
        self.task_id = task_id
        self.task_title = task_title
        self.time_remaining = 25 * 60 # 25 minutes
        self.timer = None

    def compose(self) -> ComposeResult:
        with Vertical(id="focus-dialog"):
            yield Label(f" 🚀 FOCUSING ON: {self.task_title} ", id="focus-header")
            yield Label(self.format_time(), id="timer-display", classes="large-timer")
            yield Label("[SPACE] Mark Completed  |  [ESC] Cancel Focus", id="focus-footer")

    def format_time(self) -> str:
        mins, secs = divmod(self.time_remaining, 60)
        return f"{mins:02d}:{secs:02d}"

    def on_mount(self) -> None:
        self.timer = self.set_interval(1, self.tick)

    def tick(self) -> None:
        if self.time_remaining > 0:
            self.time_remaining -= 1
            self.query_one("#timer-display", Label).update(self.format_time())
        else:
            if self.timer:
                self.timer.stop()
            self.notify_completion()

    def notify_completion(self) -> None:
        msg = f"Pomodoro beendet: {self.task_title}"
        subprocess.run(["osascript", "-e", f'display notification "{msg}" with title "🚀 utask v2.0"'])
        self.query_one("#timer-display", Label).update("DONE!")
        self.query_one("#timer-display", Label).styles.color = "green"

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
        elif event.key == "space":
            self.dismiss(self.task_id)

class InsightsScreen(ModalScreen):
    # ... existing InsightsScreen implementation ...
    """Productivity Insights Dashboard Screen."""
    def compose(self) -> ComposeResult:
        with Vertical(id="insights-dialog"):
            yield Label(" 📈   PRODUCTIVITY INSIGHTS ", id="insights-header")
            with ScrollableContainer(id="insights-scroll"):
                yield Markdown("Calculating insights...", id="insights-markdown")
            yield Label(" [ESC] Close Dashboard ", id="insights-footer")

    async def on_mount(self) -> None:
        from sqlalchemy import func
        async with AsyncSessionLocal() as session:
            # 1. Basic Stats
            total_stmt = select(func.count(Task.id))
            done_stmt = select(func.count(Task.id)).where(Task.status == "completed")
            total = (await session.execute(total_stmt)).scalar() or 0
            done = (await session.execute(done_stmt)).scalar() or 0
            open_tasks = total - done
            
            # 2. Distribution by Provider
            dist_stmt = select(Task.source_provider, func.count(Task.id)).where(Task.status == "completed").group_by(Task.source_provider)
            dist_res = await session.execute(dist_stmt)
            dist = dist_res.all()
            
            # Format Markdown
            md = f"# Statistics Overview\n\n"
            md += f"- **Total Tasks Managed:** {total}\n"
            md += f"- **Completed Tasks:** {done} ({(done/total*100):.1f}%)\n"
            md += f"- **Open Tasks:** {open_tasks}\n\n"
            
            md += "## Completions by Provider\n\n"
            if dist:
                for provider, count in dist:
                    md += f"- **{provider or 'Local'}:** {count} tasks\n"
            else:
                md += "*No data yet.*\n\n"
            
            md += "---\n\n"
            md += "💡 *Tip: High completion rates lead to better task management!*"
            
            await self.query_one("#insights-markdown", Markdown).update(md)

    def on_key(self, event) -> None:
        if event.key in ("escape", "q"):
            self.dismiss()

class FuzzySearchScreen(ModalScreen):
    """Global Fuzzy Search Modal."""
    def compose(self) -> ComposeResult:
        with Vertical(id="fuzzy-dialog"):
            yield Label(" 🔍   GLOBAL SEARCH ", id="fuzzy-header")
            yield Input(placeholder="Type to find tasks across all lists...", id="fuzzy-input")
            yield ListView(id="fuzzy-results")
            yield Label(" [ENTER] Jump to Task  |  [ESC] Cancel ", id="fuzzy-footer")

    def on_mount(self) -> None:
        self.query_one("#fuzzy-input").focus()

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "fuzzy-input":
            query = event.value.strip()
            results_view = self.query_one("#fuzzy-results", ListView)
            results_view.clear()
            
            if len(query) < 2:
                return

            async with AsyncSessionLocal() as session:
                statement = select(Task).where(Task.title.contains(query)).limit(20)
                res = await session.execute(statement)
                tasks = res.scalars().all()
                
                for task in tasks:
                    item = ListItem(Label(f"{task.title} [dim]({task.list_name})[/]"))
                    # Store metadata on the item for retrieval
                    item.task_id = task.id
                    item.list_name = task.list_name
                    results_view.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "fuzzy-results":
            item = event.item
            # Return selection data to main app
            self.dismiss({"task_id": item.task_id, "list_name": item.list_name})

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)

class TaskItem(ListItem):
    is_selected = reactive(False)

    def __init__(self, task: Task):
        super().__init__()
        self.task_id = task.id
        self.task_title = task.title
        self.task_status = task.status
        # Deterministic priority based on title
        self.priority = 2 if "!!" in self.task_title else (1 if "!" in self.task_title else 0)

    def watch_is_selected(self, value: bool) -> None:
        if value:
            self.add_class("visual-selected")
        else:
            self.remove_class("visual-selected")
        
        # Explicitly update the label content because refresh() doesn't re-compose
        try:
            label = self.query_one("#task-label", Label)
            label.update(self._get_content())
        except:
            pass # Not mounted yet

    def on_mount(self) -> None:
        if hasattr(self.app, "selected_ids"):
            self.is_selected = self.task_id in self.app.selected_ids

    def _get_content(self) -> str:
        icon = "☐   " if self.task_status != "completed" else "☑   "
        visual_marker = "[bold mauve][V][/] " if self.is_selected else ""
        prio_marker = ["", "!", "!!"][self.priority]
        prio_class = ["", "prio-med", "prio-high"][self.priority]
        
        content = f"{visual_marker}{icon}{self.task_title}"
        if prio_marker:
            content = f"{visual_marker}{icon}[{prio_class}]{prio_marker}[/] {self.task_title}"
        return content

    def compose(self) -> ComposeResult:
        yield Label(self._get_content(), id="task-label", classes="completed-task" if self.task_status == "completed" else "pending-task")

class UniversalTaskApp(App):
    CSS_PATH = "style.tcss"
    
    BINDINGS = [
        Binding("q", "quit", "Exit"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("g,g", "scroll_top", "Top", show=False),
        Binding("G", "scroll_bottom", "Bottom", show=False),
        Binding("space", "toggle_complete", "Check"),
        Binding("x", "toggle_complete", "Check", show=False),
        Binding("v", "toggle_visual", "Visual"),
        Binding("S", "postpone_tasks", "Postpone"),
        Binding("d,d", "delete_task", "Delete", show=False),
        Binding("d", "delete_task", "Delete"),
        Binding("u", "undo", "Undo"),
        Binding("a", "focus_add", "Add"),
        Binding("slash", "global_search", "Search"),
        Binding("h", "toggle_completed_visibility", "Hide Done"),
        Binding("colon", "focus_command", "Command"),
        Binding(":", "focus_command", "Command", show=False),
        Binding("s", "sync_now", "Sync"),
        Binding("p", "pomodoro_focus", "Focus"),
        Binding("i", "show_insights", "Insights"),
        Binding("question_mark", "show_help", "Help"),
        Binding("escape", "cancel_input", "Cancel", show=False),
    ]

    current_list = reactive("Reminders")
    show_completed = reactive(True)
    visual_mode = reactive(False)
    search_filter = reactive("")
    selected_ids: reactive[Set[int]] = reactive(set())
    undo_stack: List[tuple] = []
    is_syncing = reactive(False)
    current_theme = reactive("mocha")

    def watch_current_theme(self, value: str) -> None:
        self.remove_class("theme-mocha")
        self.remove_class("theme-macchiato")
        self.remove_class("theme-frappe")
        self.remove_class("theme-latte")
        self.add_class(f"theme-{value}")
        try:
            from .config import CONFIG_DIR
            (CONFIG_DIR / "theme.txt").write_text(value)
        except: pass

    def compose(self) -> ComposeResult:
        with Horizontal(id="header-stats"):
            yield Static("🚀 utask v2.0  •  ", id="header-title")
            yield Sparkline([0]*20, summary_function=max)
            yield Static("  •  [ 🟢 ONLINE ]", id="header-status")
        
        with Horizontal(id="app-grid"):
            with Vertical(id="sidebar"):
                yield Label(" 📂   LISTS ", classes="panel-header")
                yield Tree("📂 MY LISTS", id="list-tree")
            with Vertical(id="main-content"):
                yield Label(f" 📝   TASKS ", id="task-list-header", classes="panel-header")
                yield Input(placeholder="Search... (ESC to clear)", id="search-input", classes="hidden")
                yield Input(placeholder="Add Task... (Enter to save)", id="add-task-input", classes="hidden")
                yield ListView(id="task-list")
            with Vertical(id="details-panel"):
                yield Label(" ℹ️   DETAILS ", classes="panel-header")
                yield Markdown("Select a task...", id="details-content")
        
        with Container(id="command-container"):
            yield Label(":", id="command-prefix")
            yield Input(placeholder="Enter command...", id="command-input")
        
        yield Footer()

    async def on_mount(self) -> None:
        await init_db()
        # Load theme
        try:
            from .config import CONFIG_DIR
            theme_file = CONFIG_DIR / "theme.txt"
            if theme_file.exists():
                self.current_theme = theme_file.read_text().strip()
        except: pass

        await self.refresh_lists()
        tree = self.query_one("#list-tree", Tree)
        if tree.root.children:
            first_account = tree.root.children[0]
            if first_account.children:
                first_list = first_account.children[0]
                self.current_list = first_list.data
                tree.select_node(first_list)
        await self.refresh_tasks()
        await self.update_sparkline()
        # Ensure the tree has focus so keyboard commands work immediately
        self.query_one("#list-tree").focus()

    async def update_sparkline(self) -> None:
        from datetime import timedelta
        async with AsyncSessionLocal() as session:
            data = []
            for i in range(10, -1, -1):
                day = datetime.now(timezone.utc).date() - timedelta(days=i)
                stmt = select(Task).where(
                    Task.status == "completed",
                    Task.last_modified >= datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc),
                    Task.last_modified <= datetime.combine(day, datetime.max.time(), tzinfo=timezone.utc)
                )
                res = await session.execute(stmt)
                data.append(len(res.scalars().all()))
            for spark in self.query(Sparkline): spark.data = data

    def watch_is_syncing(self, value: bool) -> None:
        for header in self.query("#header-status"):
            header.update("  •  [ 🟡 BUSY ]" if value else "  •  [ 🟢 ONLINE ]")

    def watch_selected_ids(self, value: Set[int]) -> None:
        for item in self.query(TaskItem):
            item.is_selected = item.task_id in value

    def watch_current_list(self) -> None:
        self.visual_mode = False
        self.selected_ids = set()

    async def refresh_lists(self) -> None:
        for tree in self.query("#list-tree"):
            tree.clear()
            tree.root.expand()

            # Inject Smart Views
            smart = tree.root.add("[bold mauve]💡 SMART VIEWS[/]", expand=True)
            smart.add_leaf("Heute", data="_smart_today")
            smart.add_leaf("Wichtig", data="_smart_important")

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
                    else: prefix, name = "Local", full_name
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
                if self.current_list == "_smart_today":
                    from datetime import time
                    today_end = datetime.combine(datetime.now(timezone.utc).date(), time.max, tzinfo=timezone.utc)
                    statement = select(Task).where(Task.due_date <= today_end)
                elif self.current_list == "_smart_important":
                    statement = select(Task).where(Task.title.contains("!"))
                else:
                    statement = select(Task).where(Task.list_name == self.current_list)
                
                if not self.show_completed:
                    statement = statement.where(Task.status != "completed")
                
                result = await session.execute(statement)
                tasks = result.scalars().all()
                # Apply search filter
                if self.search_filter:
                    tasks = [t for t in tasks if self.search_filter.lower() in t.title.lower()]
                tasks.sort(key=lambda t: (t.status == "completed", t.title.lower()))
                for t in tasks: view.append(TaskItem(t))
            
            for header in self.query("#task-list-header"):
                display_name = self.current_list
                if display_name == "_smart_today": display_name = "Heute"
                elif display_name == "_smart_important": display_name = "Wichtig"
                
                label = f" 📝   TASKS ({display_name})"
                if self.search_filter: label += f" [🔍 {self.search_filter}]"
                if not self.show_completed: label += " [HIDDEN DONE]"
                header.update(label)

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "task-list":
            await self.update_details(event.item.task_id)

    async def update_details(self, task_id: int) -> None:
        async with AsyncSessionLocal() as session:
            task = await session.get(Task, task_id)
            if task:
                content = (f"# {task.title}\n\n"
                           f"**Status:** {task.status} | **List:** {task.list_name}\n\n"
                           f"**Modified:** {task.last_modified.strftime('%Y-%m-%d %H:%M')} | **Source:** {task.source_provider or 'Local'}\n\n"
                           f"---\n\n"
                           f"{task.description or '*No notes available.*'}")
                for detail in self.query("#details-content"):
                    await detail.update(content)

    def action_focus_command(self) -> None:
        for container in self.query("#command-container"):
            container.add_class("visible")
        for cmd_input in self.query("#command-input"):
            cmd_input.value = ""; cmd_input.focus()

    async def action_toggle_complete(self) -> None:
        task_ids = []
        if self.visual_mode and self.selected_ids:
            task_ids = list(self.selected_ids)
        else:
            for view in self.query("#task-list"):
                if view.index is not None:
                    task_ids = [view.children[view.index].task_id]
        
        if not task_ids: return

        async with AsyncSessionLocal() as session:
            for tid in task_ids:
                task = await session.get(Task, tid)
                if task:
                    task.status = "completed" if task.status != "completed" else "needsAction"
                    task.sync_pending = True
                    task.last_modified = datetime.now(timezone.utc)
                    session.add(task)
            await session.commit()
        
        if self.visual_mode:
            self.visual_mode = False
            self.selected_ids = set()
            
        await self.refresh_tasks()

    def action_scroll_top(self) -> None:
        for view in self.query("#task-list"):
            if view.children: view.index = 0

    def action_scroll_bottom(self) -> None:
        for view in self.query("#task-list"):
            if view.children: view.index = len(view.children) - 1

    def action_toggle_visual(self) -> None:
        self.visual_mode = not self.visual_mode
        if self.visual_mode:
            # Immediately select focused item
            for view in self.query("#task-list"):
                if view.index is not None:
                    self.selected_ids = {view.children[view.index].task_id}
        else:
            self.selected_ids = set()
        self.notify(f"Visual Mode: {'ON' if self.visual_mode else 'OFF'}")

    async def action_delete_task(self) -> None:
        task_ids = []
        if self.visual_mode and self.selected_ids:
            task_ids = list(self.selected_ids)
        else:
            for view in self.query("#task-list"):
                if view.index is not None:
                    task_ids = [view.children[view.index].task_id]
        
        if not task_ids: return

        bulk_data = []
        async with AsyncSessionLocal() as session:
            for tid in task_ids:
                task = await session.get(Task, tid)
                if task:
                    task_data = {c.name: getattr(task, c.name) for c in task.__table__.columns}
                    bulk_data.append(task_data)
                    await session.delete(task)
            await session.commit()
        
        if bulk_data:
            self.undo_stack.append(("bulk_delete", bulk_data))
        
        if self.visual_mode:
            self.visual_mode = False
            self.selected_ids = set()
            
        await self.refresh_tasks()

    async def action_undo(self) -> None:
        if not self.undo_stack:
            self.notify("Nothing to undo"); return
        action, data = self.undo_stack.pop()
        async with AsyncSessionLocal() as session:
            if action == "delete":
                session.add(Task(**data))
            elif action == "bulk_delete":
                for task_data in data:
                    session.add(Task(**task_data))
            await session.commit()
        await self.refresh_tasks()
        self.notify("Restored tasks")

    def action_focus_add(self) -> None:
        for inp in self.query("#add-task-input"):
            inp.remove_class("hidden"); inp.focus()

    def action_focus_search(self) -> None:
        for inp in self.query("#search-input"):
            inp.remove_class("hidden"); inp.focus()

    async def action_toggle_completed_visibility(self) -> None:
        self.show_completed = not self.show_completed
        await self.refresh_tasks()

    async def action_sync_now(self) -> None:
        self.is_syncing = True
        from .main import get_engine
        await get_engine().sync_all()
        self.is_syncing = False
        await self.refresh_lists(); await self.refresh_tasks(); self.notify("Sync completed")

    async def action_postpone_tasks(self) -> None:
        from datetime import timedelta
        task_ids = []
        if self.visual_mode and self.selected_ids:
            task_ids = list(self.selected_ids)
        else:
            for view in self.query("#task-list"):
                if view.index is not None:
                    task_ids = [view.children[view.index].task_id]
        
        if not task_ids: return

        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        async with AsyncSessionLocal() as session:
            for tid in task_ids:
                task = await session.get(Task, tid)
                if task:
                    task.due_date = tomorrow
                    task.sync_pending = True
                    task.last_modified = datetime.now(timezone.utc)
                    session.add(task)
            await session.commit()
        
        if self.visual_mode:
            self.visual_mode = False
            self.selected_ids = set()
            
        await self.refresh_tasks()
        self.notify(f"Postponed {len(task_ids)} tasks to tomorrow")

    def action_pomodoro_focus(self) -> None:
        for view in self.query("#task-list"):
            if view.index is not None:
                item = view.children[view.index]
                if item.task_status != "completed":
                    self.push_screen(
                        FocusScreen(item.task_id, item.task_title),
                        callback=self.handle_focus_finish
                    )
                else:
                    self.notify("Task is already completed!", severity="warning")

    async def handle_focus_finish(self, task_id: Optional[int]) -> None:
        if task_id:
            async with AsyncSessionLocal() as session:
                task = await session.get(Task, task_id)
                if task:
                    task.status = "completed"
                    task.last_modified = datetime.now(timezone.utc)
                    session.add(task)
                    await session.commit()
            await self.refresh_tasks()
            self.notify(f"Task completed during focus!")

    def action_show_help(self) -> None:
        if not isinstance(self.screen, HelpScreen): self.push_screen(HelpScreen())

    def action_show_insights(self) -> None:
        if not isinstance(self.screen, InsightsScreen): self.push_screen(InsightsScreen())

    def action_global_search(self) -> None:
        self.push_screen(FuzzySearchScreen(), callback=self.handle_jump_to_task)

    async def handle_jump_to_task(self, result: Optional[dict]) -> None:
        if result:
            target_list = result["list_name"]
            target_id = result["task_id"]
            
            # 1. Switch list
            self.current_list = target_list
            
            # 2. Select node in tree (visual)
            for tree in self.query("#list-tree"):
                # We need to find the node with data == target_list
                def find_and_select(node):
                    if node.data == target_list:
                        tree.select_node(node)
                        return True
                    for child in node.children:
                        if find_and_select(child): return True
                    return False
                find_and_select(tree.root)

            # 3. Refresh tasks
            await self.refresh_tasks()
            
            # 4. Focus and highlight the specific task in the list
            for view in self.query("#task-list"):
                for idx, child in enumerate(view.children):
                    if getattr(child, "task_id", None) == target_id:
                        view.index = idx
                        view.focus()
                        break

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self.search_filter = event.value.strip()
            self.run_worker(self.refresh_tasks())

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "command-input":
            raw_cmd = event.value.strip(); cmd = raw_cmd.lower()
            for container in self.query("#command-container"): container.remove_class("visible")
            if cmd in ("q", "quit"): self.exit()
            elif cmd in ("help", "?"): self.push_screen(HelpScreen())
            elif cmd in ("h", "hide", "show"): await self.action_toggle_completed_visibility()
            elif cmd == "sync": await self.action_sync_now()
            elif cmd.startswith("delete list"):
                list_name = raw_cmd[11:].strip().strip('"').strip("'")
                if list_name: await self.action_delete_list(list_name)
                else: self.notify("Please specify a list name", severity="error")
            elif cmd.startswith("create list "):
                parts = raw_cmd[12:].strip().split('"')
                # Extract name inside quotes if present
                if len(parts) >= 3:
                    lname = parts[1]
                    plabel = parts[2].strip() or "Apple"
                else:
                    sub_parts = raw_cmd[12:].strip().split()
                    lname = sub_parts[0] if sub_parts else ""
                    plabel = sub_parts[1] if len(sub_parts) > 1 else "Apple"
                
                if lname: await self.action_create_list(lname, plabel)
                else: self.notify("Usage: create list \"Name\" [Provider]", severity="error")
            elif cmd.startswith("move "):
                target_label = raw_cmd[5:].strip().strip('"').strip("'")
                if target_label: await self.action_magic_move(target_label)
                else: self.notify("Please specify a target provider label", severity="error")
            elif cmd.startswith("theme "):
                flavor = raw_cmd[6:].strip().lower()
                if flavor in ("mocha", "macchiato", "frappe", "latte"):
                    self.current_theme = flavor
                    self.notify(f"Theme switched to {flavor.capitalize()}")
                else:
                    self.notify("Invalid theme. Use mocha, macchiato, frappe, or latte.", severity="error")
            elif cmd.startswith("template add "):
                # Usage: :template add "Name" "Title" "Desc"
                parts = raw_cmd[13:].strip().split('"')
                if len(parts) >= 5:
                    t_name = parts[1]; t_title = parts[3]; t_desc = parts[5]
                    async with AsyncSessionLocal() as session:
                        session.add(TaskTemplate(name=t_name, title=t_title, description=t_desc, list_name=self.current_list))
                        await session.commit()
                    self.notify(f"Template '{t_name}' saved")
                else: self.notify("Usage: :template add \"Name\" \"Title\" \"Description\"", severity="error")
            elif cmd.startswith("use "):
                t_name = raw_cmd[4:].strip().strip('"')
                async with AsyncSessionLocal() as session:
                    stmt = select(TaskTemplate).where(TaskTemplate.name == t_name)
                    res = await session.execute(stmt)
                    tpl = res.scalar_one_or_none()
                    if tpl:
                        session.add(Task(title=tpl.title, description=tpl.description, list_name=tpl.list_name or self.current_list))
                        await session.commit()
                        self.notify(f"Created task from template '{t_name}'")
                        await self.refresh_tasks()
                    else: self.notify(f"Template '{t_name}' not found", severity="error")
            elif cmd.startswith("recur "):
                freq = raw_cmd[6:].strip().lower()
                if freq in ("daily", "weekly", "monthly", "none"):
                    freq = None if freq == "none" else freq
                    for view in self.query("#task-list"):
                        if view.index is not None:
                            task_id = view.children[view.index].task_id
                            async with AsyncSessionLocal() as session:
                                task = await session.get(Task, task_id)
                                if task:
                                    task.recurrence = freq
                                    session.add(task)
                                    await session.commit()
                            self.notify(f"Recurrence set to {freq}")
                            await self.refresh_tasks()
                else: self.notify("Usage: :recur [daily|weekly|monthly|none]", severity="error")
            elif cmd == "log":
                self.push_screen(HelpScreen()) # Placeholder: Use a real log screen later or repurpose Help
                async with AsyncSessionLocal() as session:
                    stmt = select(SyncLog).order_by(SyncLog.timestamp.desc()).limit(20)
                    logs = (await session.execute(stmt)).scalars().all()
                    content = "# 🛰️ Sync History\n\n"
                    if logs:
                        for l in logs:
                            content += f"**[{l.timestamp.strftime('%H:%M:%S')}]** {l.event}: {l.details}\n"
                    else:
                        content += "*No sync events recorded yet.*"
                    # We reuse HelpScreen for a quick log view
                    self.push_screen(HelpScreen())
                    for detail in self.query("#help-markdown"):
                        await detail.update(content)
                    for header in self.query("#help-header"):
                        header.update(" 📜   SYNC HISTORY (ESC/Q to exit) ")
        elif event.input.id == "add-task-input":
            title = event.value.strip()
            if title:
                async with AsyncSessionLocal() as session:
                    session.add(Task(title=title, list_name=self.current_list, sync_pending=True))
                    await session.commit()
                event.input.value = ""; event.input.add_class("hidden")
                await self.refresh_tasks()
        elif event.input.id == "search-input":
            event.input.add_class("hidden")
        
        # Focus back to a sensible default after submission
        if self.query("#task-list"):
            self.query_one("#task-list").focus()
        elif self.query("#list-tree"):
            self.query_one("#list-tree").focus()

    async def action_delete_list(self, list_name: str) -> None:
        self.notify(f"Deleting list '{list_name}' everywhere...", severity="warning")
        from .main import get_engine
        await get_engine().delete_list(list_name)
        if self.current_list == list_name: self.current_list = "Reminders"
        await self.refresh_lists(); await self.refresh_tasks(); self.notify(f"Deleted list: {list_name}")

    async def action_magic_move(self, target_label: str) -> None:
        task_ids = []
        if self.visual_mode and self.selected_ids:
            task_ids = list(self.selected_ids)
        else:
            for view in self.query("#task-list"):
                if view.index is not None:
                    task_ids = [view.children[view.index].task_id]
        
        if not task_ids:
            self.notify("No tasks selected to move", severity="warning")
            return

        self.notify(f"Moving {len(task_ids)} tasks to {target_label}...", severity="warning")
        from .main import get_engine
        success_count = await get_engine().move_tasks(task_ids, target_label)
        
        if success_count > 0:
            self.visual_mode = False
            self.selected_ids = set()
            await self.refresh_lists()
            await self.refresh_tasks()
            self.notify(f"Successfully moved {success_count} tasks to {target_label}!")
        else:
            self.notify(f"Failed to move tasks. Check if provider '{target_label}' exists.", severity="error")

    async def action_create_list(self, name: str, provider_label: str) -> None:
        self.notify(f"Creating list '{name}' on {provider_label}...")
        from .main import get_engine
        success = await get_engine().create_list(name, provider_label)
        if success:
            await self.refresh_lists()
            self.notify(f"✅ List '{name}' created on {provider_label}")
        else:
            self.notify(f"❌ Failed to create list on {provider_label}. Check if provider exists.", severity="error")

    def action_cancel_input(self) -> None:
        for container in self.query("#command-container"): container.remove_class("visible")
        for inp in self.query("#add-task-input"): inp.add_class("hidden")
        for inp in self.query("#search-input"):
            inp.add_class("hidden")
            if self.search_filter:
                self.search_filter = ""; inp.value = ""; self.run_worker(self.refresh_tasks())
        for tree in self.query("#list-tree"): tree.focus()

    def action_cursor_down(self) -> None:
        for view in self.query("#task-list"):
            if view.index is not None and view.index < len(view.children) - 1:
                view.index += 1
                if self.visual_mode:
                    self.selected_ids = set(list(self.selected_ids) + [view.children[view.index].task_id])

    def action_cursor_up(self) -> None:
        for view in self.query("#task-list"):
            if view.index is not None and view.index > 0:
                view.index -= 1
                if self.visual_mode:
                    self.selected_ids = set(list(self.selected_ids) + [view.children[view.index].task_id])

if __name__ == "__main__":
    UniversalTaskApp().run()
