"""Due dates round-trip through the sync engine, against a throwaway database and a fake provider.
Run: .venv/bin/python tests/test_due_sync.py"""
import asyncio, tempfile
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, select
from task_sync import core
from task_sync.models import Task, SyncMapping
from task_sync.providers.base import RemoteTask
from task_sync.tui import split_due

DAY = datetime(2026, 12, 24, tzinfo=timezone.utc)

class Fake:
    name, account_label = "fake", "Fake"
    def __init__(self): self.calls, self.remote_due = [], None
    async def create_task(self, title, list_name): self.calls.append(("create", title)); return "r1"
    async def update_task(self, remote_id, title=None, status=None, due=None, set_due=False):
        self.calls.append(("update", set_due, due)); return True
    async def get_tasks(self, list_name=None):
        return [RemoteTask(remote_id="r1", title="t", status="needsAction", list_name="l", last_modified=datetime.now(timezone.utc), due=self.remote_due)]

async def main():
    db = tempfile.mktemp(suffix=".db")
    eng = create_async_engine(f"sqlite+aiosqlite:///{db}")
    async with eng.begin() as c: await c.run_sync(SQLModel.metadata.create_all)
    core.AsyncSessionLocal = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    prov = Fake(); sync = core.SyncEngine([prov])

    async with core.AsyncSessionLocal() as s:  # a new local task with a due date is created remotely, then dated
        s.add(Task(title="t", list_name="[Fake] l", due_date=DAY, sync_pending=True)); await s.commit()
    await sync._propagate()
    assert prov.calls == [("create", "t"), ("update", True, DAY)], prov.calls

    async with core.AsyncSessionLocal() as s:  # an edit sends the date along
        t = (await s.execute(select(Task))).scalar_one(); t.sync_pending = True; s.add(t); await s.commit()
    prov.calls.clear(); await sync._propagate()
    assert prov.calls[-1][:2] == ("update", True), prov.calls

    prov.remote_due = datetime(2027, 1, 5, tzinfo=timezone.utc)  # a date changed on the phone is pulled in
    await sync._update_local_db("fake", await prov.get_tasks(), "[Fake] l")
    async with core.AsyncSessionLocal() as s:
        assert (await s.execute(select(Task))).scalar_one().due_date.date() == prov.remote_due.date()

    assert split_due("Call Anna @24.12.")[1].month == 12 and split_due("a@b.de") == ("a@b.de", None)
    print("ok")

asyncio.run(main())
