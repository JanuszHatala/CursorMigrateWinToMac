"""Rewrite Windows paths inside VS Code/Cursor SQLite state databases."""

from __future__ import annotations

import json
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from cursor_mac_migrate.paths import PathRewriter

TABLES = ("ItemTable", "cursorDiskKV")


@dataclass
class SqliteRewriteStats:
    path: Path
    rows_seen: int = 0
    rows_changed: int = 0
    skipped_binary: int = 0


def checkpoint_and_copy(db_path: Path, backup_path: Path) -> None:
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        shutil.copy2(db_path, backup_path)
    for suffix in ("-wal", "-shm"):
        side = Path(str(db_path) + suffix)
        if side.exists():
            shutil.copy2(side, Path(str(backup_path) + suffix))
    if not db_path.exists():
        return
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.commit()
    finally:
        conn.close()


def rewrite_db(
    db_path: Path,
    rewriter: PathRewriter,
    *,
    dry_run: bool = False,
) -> SqliteRewriteStats:
    stats = SqliteRewriteStats(path=db_path)
    if not db_path.exists():
        return stats
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for table in TABLES:
            if table not in tables:
                continue
            columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
            if "key" not in columns or "value" not in columns:
                continue
            rows = list(conn.execute(f"SELECT key, value FROM {table}"))
            updates: list[tuple[object, object]] = []
            for key, value in rows:
                stats.rows_seen += 1
                new_key, key_changed, key_binary = _rewrite_cell(key, rewriter)
                new_value, value_changed, value_binary = _rewrite_cell(value, rewriter)
                if key_binary or value_binary:
                    stats.skipped_binary += 1
                if key_changed or value_changed:
                    stats.rows_changed += 1
                    updates.append((new_key, new_value, key))
            if dry_run or not updates:
                continue
            conn.executemany(
                f"UPDATE {table} SET key = ?, value = ? WHERE key = ?",
                updates,
            )
        if not dry_run:
            conn.commit()
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise RuntimeError(f"{db_path}: integrity_check failed: {integrity}")
    finally:
        conn.close()
    return stats


def _rewrite_cell(cell, rewriter: PathRewriter) -> tuple[object, bool, bool]:
    if cell is None:
        return cell, False, False
    if isinstance(cell, bytes):
        try:
            text = cell.decode("utf-8")
        except UnicodeDecodeError:
            return cell, False, True
        new_text = _rewrite_text(text, rewriter)
        if new_text == text:
            return cell, False, False
        return new_text.encode("utf-8"), True, False
    if isinstance(cell, str):
        new_text = _rewrite_text(cell, rewriter)
        return new_text, new_text != cell, False
    return cell, False, False


def _rewrite_text(text: str, rewriter: PathRewriter) -> str:
    stripped = text.lstrip()
    if stripped[:1] in "{[":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return rewriter.rewrite_string(text)
        rewritten = rewriter.rewrite_obj(data)
        if rewritten == data:
            return text
        return json.dumps(rewritten, ensure_ascii=False, separators=(",", ":"))
    return rewriter.rewrite_string(text)
