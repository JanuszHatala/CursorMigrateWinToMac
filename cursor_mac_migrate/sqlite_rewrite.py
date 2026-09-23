"""Rewrite Windows paths inside VS Code/Cursor SQLite state databases."""

from __future__ import annotations

import gzip
import json
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from cursor_mac_migrate.paths import PathRewriter

TABLES = ("ItemTable", "cursorDiskKV")
_SKIP_DB_DIRS = {
    "Cache",
    "CachedData",
    "CachedExtensionVSIXs",
    "Code Cache",
    "GPUCache",
    "logs",
    "Crashpad",
    "Service Worker",
    "blob_storage",
    "node_modules",
    ".git",
    "extensions",
}


def discover_state_dbs(user_dir: Path) -> list[Path]:
    """Every Cursor state database under the app support folder, plus workspace copies."""
    roots = [user_dir]
    if user_dir.parent.is_dir():
        roots.append(user_dir.parent)
    found: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix != ".vscdb" and not path.name.endswith(".vscdb.backup"):
                continue
            if any(part in _SKIP_DB_DIRS or part.startswith("User.mac-migrate-backup") for part in path.parts):
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            found.append(path)
    return sorted(found)


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
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
        for table in tables:
            qtable = _quote(table)
            columns = [row[1] for row in conn.execute(f"PRAGMA table_info({qtable})")]
            if not columns:
                continue
            col_sql = ", ".join(_quote(column) for column in columns)
            try:
                rows = list(conn.execute(f"SELECT rowid AS _rid, {col_sql} FROM {qtable}"))
            except sqlite3.OperationalError:
                continue
            updates: list[tuple] = []
            for row in rows:
                stats.rows_seen += 1
                new_values: list[object] = []
                changed = False
                binary = False
                for column in columns:
                    new_cell, cell_changed, cell_binary = _rewrite_cell(row[column], rewriter)
                    new_values.append(new_cell)
                    changed = changed or cell_changed
                    binary = binary or cell_binary
                if binary:
                    stats.skipped_binary += 1
                if changed:
                    stats.rows_changed += 1
                    updates.append((*new_values, row["_rid"]))
            if dry_run or not updates:
                continue
            set_sql = ", ".join(f"{_quote(column)} = ?" for column in columns)
            conn.executemany(
                f"UPDATE {qtable} SET {set_sql} WHERE rowid = ?",
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


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _rewrite_cell(cell, rewriter: PathRewriter) -> tuple[object, bool, bool]:
    if cell is None:
        return cell, False, False
    if isinstance(cell, bytes) and cell[:2] == b"\x1f\x8b":
        try:
            text = gzip.decompress(cell).decode("utf-8")
        except (OSError, EOFError, UnicodeDecodeError, gzip.BadGzipFile):
            return cell, False, True
        new_text = _rewrite_text(text, rewriter)
        if new_text == text:
            return cell, False, False
        return gzip.compress(new_text.encode("utf-8")), True, False
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
