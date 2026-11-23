#!/usr/bin/env python3
"""Opt-in, offline staging of Personal AI OS notes into a private LifeOS USER tree.

Never reads GitHub or ChatGPT automatically. Dry-run unless --apply is explicit.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

PROFILE_FILES = (
    "PROFILE.md", "GOALS.md", "PRINCIPLES.md", "PROJECTS.md",
    "KNOWLEDGE.md", "DECISIONS.md", "JOURNAL.md", "SKILLS.md",
)
TARGET_SUBDIR = ("IMPORTS", "PERSONAL_AI_OS")


def _safe_directory(path: Path, label: str) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"{label} must be an existing, non-symlink directory")
    return path.resolve()


def _safe_child_directory(parent: Path, name: str, apply: bool) -> Path:
    child = parent / name
    if child.is_symlink() or (child.exists() and not child.is_dir()):
        raise ValueError(f"unsafe {name} directory in destination")
    if apply and not child.exists():
        child.mkdir(mode=0o700)  # fails instead of following an unexpected existing file
    return child


def stage(source: Path, user_dir: Path, apply: bool = False) -> dict:
    """Return metadata only; no private file contents are ever reported."""
    source = _safe_directory(source, "source")
    user_dir = _safe_directory(user_dir, "LifeOS USER directory")
    if user_dir.name != "USER" or not (user_dir / "CONFIG").is_dir():
        raise ValueError("destination is not a recognized installed LifeOS USER tree")
    if "LifeOS/install/USER" in user_dir.as_posix():
        raise ValueError("refusing to write into the public LifeOS USER template")
    # Source and destination must be separate. Avoid an export already inside USER.
    if source == user_dir or user_dir in source.parents or source in user_dir.parents:
        raise ValueError("source and destination directories must be separate")

    staged = user_dir.joinpath(*TARGET_SUBDIR)
    candidate_names = []
    for name in PROFILE_FILES:
        p = source / name
        if p.is_symlink() or (p.exists() and not p.is_file()):
            raise ValueError(f"unsupported source file type: {name}")
        if p.is_file():
            candidate_names.append(name)
    if not candidate_names:
        raise ValueError("no supported Personal AI OS Markdown files found")

    # Preflight every destination before any writing; fail closed on conflicts.
    base = user_dir
    for part in TARGET_SUBDIR:
        base = _safe_child_directory(base, part, False)
    rows = []
    for name in PROFILE_FILES:
        src = source / name
        dst = staged / name
        if not src.is_file():
            status = "missing_source"
        elif dst.is_symlink() or (dst.exists() and not dst.is_file()):
            status = "unsafe_destination"
        elif not dst.exists():
            status = "new"
        elif src.read_bytes() == dst.read_bytes():
            status = "identical"
        else:
            status = "conflict"
        rows.append({"file": name, "status": status})

    blocked = any(x["status"] in ("conflict", "unsafe_destination") for x in rows)
    if apply and not blocked:
        base = user_dir
        for part in TARGET_SUBDIR:
            base = _safe_child_directory(base, part, True)
        for item in rows:
            if item["status"] != "new":
                continue
            name = item["file"]
            # O_EXCL refuses overwrites, O_NOFOLLOW (where available) refuses symlinks.
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(staged / name, flags, 0o600)
            try:
                with os.fdopen(fd, "wb") as output:
                    output.write((source / name).read_bytes())
            except Exception:
                (staged / name).unlink(missing_ok=True)
                raise
            item["status"] = "staged"
    return {
        "ok": not blocked,
        "dry_run": not apply,
        "count_found": len(candidate_names),
        "destination": "USER/IMPORTS/PERSONAL_AI_OS",
        "files": rows,
        "next": "Review imported notes during LifeOS interview; do not auto-write TELOS or commit personal data.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="source", type=Path, required=True, help="local export directory containing Markdown files")
    parser.add_argument("--user-dir", type=Path, required=True, help="installed, private LifeOS USER directory")
    parser.add_argument("--apply", action="store_true", help="explicitly stage missing files (default: preview only)")
    args = parser.parse_args(argv)
    try:
        result = stage(args.source, args.user_dir, args.apply)
    except (ValueError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
