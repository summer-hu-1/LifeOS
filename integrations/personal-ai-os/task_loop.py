#!/usr/bin/env python3
"""Personal AI OS: local-only task/outbox MVP (no network or push delivery)."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys
import uuid

STORAGE = ("MEMORY", "_PERSONAL_AI_OS")
UTC = timezone.utc


def iso_time(value: str | None = None) -> str:
    dt = datetime.now(UTC) if value is None else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("datetime must have an explicit timezone offset (e.g. +08:00)")
    return dt.astimezone(UTC).isoformat(timespec="seconds")


def user_root(path: Path) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise ValueError("USER path must be a real, existing local directory")
    resolved = path.resolve()
    if resolved.name != "USER" or not (resolved / "CONFIG").is_dir():
        raise ValueError("expected an installed LifeOS USER directory containing CONFIG/")
    if "/LifeOS/install/USER" in resolved.as_posix():
        raise ValueError("refusing to use public LifeOS USER templates")
    return resolved


def _subdirectory(parent: Path, name: str) -> Path:
    p = parent / name
    if p.is_symlink() or (p.exists() and not p.is_dir()):
        raise ValueError(f"unsafe storage directory: {name}")
    if not p.exists():
        p.mkdir(mode=0o700)
    return p


def connect(user_dir: Path) -> sqlite3.Connection:
    root = user_root(user_dir)
    for part in STORAGE:
        root = _subdirectory(root, part)
    db_path = root / "tasks.sqlite3"
    if db_path.is_symlink() or (db_path.exists() and not db_path.is_file()):
        raise ValueError("unsafe task database path")
    # Respect private storage by default; no public GitHub repository is touched.
    old_mask = os.umask(0o077)
    try:
        db = sqlite3.connect(db_path)
    finally:
        os.umask(old_mask)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS tasks (
      id TEXT PRIMARY KEY, title TEXT NOT NULL, domain TEXT NOT NULL,
      due_at TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('active','completed')),
      created_at TEXT NOT NULL, completed_at TEXT
    );
    CREATE TABLE IF NOT EXISTS outbox (
      task_id TEXT PRIMARY KEY REFERENCES tasks(id),
      state TEXT NOT NULL CHECK(state IN ('queued','delivered','acknowledged')),
      queued_at TEXT NOT NULL, delivered_at TEXT, receipt TEXT, acknowledged_at TEXT
    );
    CREATE TABLE IF NOT EXISTS events (
      seq INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL REFERENCES tasks(id),
      kind TEXT NOT NULL, at TEXT NOT NULL, evidence TEXT
    );
    """)
    return db


def create_task(db: sqlite3.Connection, title: str, due: str, domain: str = "general") -> dict:
    title = title.strip()
    if not title or len(title) > 250:
        raise ValueError("title must contain 1-250 characters")
    if not domain or len(domain) > 40 or not all(ch.isalnum() or ch in "-_" for ch in domain):
        raise ValueError("domain must use simple letters, numbers, dash or underscore")
    task_id = uuid.uuid4().hex
    due_at, now = iso_time(due), iso_time()
    with db:
        db.execute("INSERT INTO tasks VALUES (?,?,?,?,?,?,?)",
                   (task_id, title, domain, due_at, "active", now, None))
        db.execute("INSERT INTO events(task_id,kind,at) VALUES(?,?,?)",
                   (task_id, "created", now))
    return {"id": task_id, "due_at": due_at, "status": "active"}


def tick(db: sqlite3.Connection, at: str | None = None) -> list[dict]:
    now = iso_time(at)
    with db:
        tasks = db.execute("""
          SELECT id,title,due_at FROM tasks
          WHERE status='active' AND due_at<=?
          AND id NOT IN (SELECT task_id FROM outbox)
          ORDER BY due_at,id
        """, (now,)).fetchall()
        for task in tasks:
            db.execute("INSERT INTO outbox(task_id,state,queued_at) VALUES(?,'queued',?)",
                       (task["id"], now))
            db.execute("INSERT INTO events(task_id,kind,at) VALUES(?,?,?)",
                       (task["id"], "notification_queued", now))
    return [{"id": t["id"], "title": t["title"], "due_at": t["due_at"],
             "state": "queued_not_sent"} for t in tasks]


def transition(db: sqlite3.Connection, task_id: str, action: str,
               receipt: str | None = None) -> dict:
    if action not in {"delivered", "acknowledged", "completed"}:
        raise ValueError("unknown action")
    now = iso_time()
    with db:
        task = db.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
        if task is None:
            raise ValueError("unknown task")
        if action == "completed":
            if task["status"] == "completed":
                return {"id": task_id, "status": "completed", "already": True}
            db.execute("UPDATE tasks SET status='completed',completed_at=? WHERE id=?",
                       (now, task_id))
        else:
            row = db.execute("SELECT state,receipt FROM outbox WHERE task_id=?",
                             (task_id,)).fetchone()
            if row is None:
                raise ValueError("task has no queued notification")
            if task["status"] != "active":
                raise ValueError("cannot change notification state for a completed task")
            if action == "delivered":
                if not receipt or not receipt.strip():
                    raise ValueError("a delivery receipt is required; stdout is not proof of delivery")
                if row["state"] in ("delivered", "acknowledged"):
                    if row["receipt"] != receipt:
                        raise ValueError("notification already has a different receipt")
                    return {"id": task_id, "status": row["state"], "already": True}
                db.execute("""UPDATE outbox SET state='delivered',delivered_at=?,receipt=?
                              WHERE task_id=?""", (now, receipt, task_id))
            else:
                if row["state"] == "acknowledged":
                    return {"id": task_id, "status": action, "already": True}
                if row["state"] != "delivered":
                    raise ValueError("must confirm delivery before acknowledgement")
                db.execute("""UPDATE outbox SET state='acknowledged',acknowledged_at=?
                              WHERE task_id=?""", (now, task_id))
        db.execute("INSERT INTO events(task_id,kind,at,evidence) VALUES(?,?,?,?)",
                   (task_id, action, now, receipt if action == "delivered" else None))
    return {"id": task_id, "status": action}


def report(db: sqlite3.Connection) -> dict:
    statuses = {r["status"]: r["n"] for r in
                db.execute("SELECT status,COUNT(*) n FROM tasks GROUP BY status")}
    outbox = {r["state"]: r["n"] for r in
              db.execute("SELECT state,COUNT(*) n FROM outbox GROUP BY state")}
    count = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    return {"tasks": statuses, "notification_outbox": outbox, "event_count": count,
            "delivery_scope": "local_outbox_only"}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--user-dir", type=Path, required=True,
                   help="existing *private* LifeOS USER folder (never the public source template)")
    commands = p.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    add = commands.add_parser("add")
    add.add_argument("--title", required=True)
    add.add_argument("--due", required=True, help="ISO 8601 with timezone, e.g. 2026-11-24T09:00:00+08:00")
    add.add_argument("--domain", default="general")
    tickp = commands.add_parser("tick")
    tickp.add_argument("--at", help="test clock, ISO 8601 with timezone; default now")
    for name in ("delivered", "acknowledged", "completed"):
        sub = commands.add_parser(name)
        sub.add_argument("--id", required=True)
        if name == "delivered":
            sub.add_argument("--receipt", required=True,
                             help="real external delivery evidence; no fake receipts")
    commands.add_parser("report")
    args = p.parse_args(argv)
    try:
        with connect(args.user_dir) as db:
            if args.command == "init":
                result = {"ok": True, "storage": "USER/MEMORY/_PERSONAL_AI_OS"}
            elif args.command == "add":
                result = create_task(db, args.title, args.due, args.domain)
            elif args.command == "tick":
                result = {"queued": tick(db, args.at), "sent": 0}
            elif args.command in {"delivered", "acknowledged", "completed"}:
                result = transition(db, args.id, args.command,
                                    getattr(args, "receipt", None))
            else:
                result = report(db)
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
