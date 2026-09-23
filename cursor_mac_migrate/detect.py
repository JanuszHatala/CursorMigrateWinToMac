"""Scan copied Cursor data for Windows paths that still need a map."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from cursor_mac_migrate.files_rewrite import iter_text_files
from cursor_mac_migrate.sidecars import sidecar_roots
from cursor_mac_migrate.paths import extract_windows_paths, looks_like_windows_path, suggest_roots
from cursor_mac_migrate.sqlite_rewrite import discover_state_dbs
from cursor_mac_migrate.workspace_relink import (
    file_uri_to_native,
    read_workspace_json,
    workspace_target_from_json,
)


@dataclass
class ScanResult:
    windows_paths: Counter = field(default_factory=Counter)
    workspace_uris: list[tuple[str, str, str]] = field(default_factory=list)
    skills: list[Path] = field(default_factory=list)
    code_workspaces: list[str] = field(default_factory=list)
    python_hits: list[str] = field(default_factory=list)
    intellij_hits: list[str] = field(default_factory=list)
    files_with_windows: list[Path] = field(default_factory=list)


def scan_tree(user_dir: Path, dot_cursor: Path) -> ScanResult:
    result = ScanResult()
    for root in (user_dir, dot_cursor, *sidecar_roots(user_dir)):
        if not root.exists():
            continue
        for path in iter_text_files(root):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            found = extract_windows_paths(text)
            if found:
                result.files_with_windows.append(path)
            for item in found:
                result.windows_paths[item] += 1
                _classify(item, text, result)

    storage = user_dir / "workspaceStorage"
    if storage.is_dir():
        for entry in storage.iterdir():
            meta = entry / "workspace.json"
            if not meta.exists():
                continue
            try:
                data = read_workspace_json(meta)
            except (OSError, json.JSONDecodeError):
                continue
            target = workspace_target_from_json(data)
            if not target:
                continue
            kind, uri = target
            result.workspace_uris.append((entry.name, kind, uri))
            native = file_uri_to_native(uri)
            for item in extract_windows_paths(native) or [native]:
                result.windows_paths[item] += 1
            if kind == "workspace":
                result.code_workspaces.append(native)

    for db in _sqlite_files(user_dir):
        _scan_sqlite(db, result)

    skills_root = dot_cursor / "skills"
    if skills_root.is_dir():
        result.skills = sorted(
            path.parent for path in skills_root.rglob("SKILL.md")
        )
    return result


def _sqlite_files(user_dir: Path) -> list[Path]:
    return discover_state_dbs(user_dir)


def _scan_sqlite(db_path: Path, result: ScanResult) -> None:
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for table in tables:
            if table.startswith("sqlite_"):
                continue
            qtable = '"' + table.replace('"', '""') + '"'
            try:
                columns = [row[1] for row in conn.execute(f"PRAGMA table_info({qtable})")]
            except sqlite3.Error:
                continue
            for column in columns:
                qcolumn = '"' + column.replace('"', '""') + '"'
                try:
                    rows = conn.execute(f"SELECT {qcolumn} FROM {qtable}")
                except sqlite3.Error:
                    continue
                for (value,) in rows:
                    text = _cell_text(value)
                    if not text or not looks_like_windows_path(text):
                        continue
                    found = extract_windows_paths(text)
                    for item in found:
                        result.windows_paths[item] += 1
                        _classify(item, text, result)
    finally:
        conn.close()


def _cell_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes) and value[:2] == b"\x1f\x8b":
        import gzip

        try:
            value = gzip.decompress(value)
        except (OSError, EOFError, gzip.BadGzipFile):
            return ""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return ""
    return str(value)


def _classify(path: str, blob: str, result: ScanResult) -> None:
    lower = (path + " " + blob[:200]).lower()
    if "python.exe" in lower or "\\python\\" in lower or "/python/" in path.lower():
        if path not in result.python_hits:
            result.python_hits.append(path)
    if "idea64.exe" in lower or "intellij" in lower or "jetbrains" in lower:
        if path not in result.intellij_hits:
            result.intellij_hits.append(path)


def proposed_map(scan: ScanResult, mac_home: Path) -> dict:
    roots = suggest_roots(list(scan.windows_paths))
    homes = [r for r in roots if _looks_like_home(r)]
    workspaces = [p for p in scan.code_workspaces]
    other = [r for r in roots if r not in homes and not r.lower().endswith(".code-workspace")]
    win_home = homes[0] if homes else "C:\\Users\\YOUR_WINDOWS_USER"
    return {
        "homes": {"windows": win_home, "mac": str(mac_home)},
        "roots": [
            {
                "windows": root,
                "mac": _guess_mac(root, win_home, mac_home),
                "kind": "folder",
            }
            for root in other
        ],
        "workspaces": [
            {
                "windows": ws,
                "mac": _guess_mac(ws, win_home, mac_home),
            }
            for ws in sorted(set(workspaces))
        ],
        "tools": {
            "python": "/usr/bin/python3",
            "intellij": "/Applications/IntelliJ IDEA.app",
        },
        "cursor_user_dir": str(mac_home / "Library/Application Support/Cursor/User"),
        "dot_cursor": str(mac_home / ".cursor"),
    }


def _looks_like_home(path: str) -> bool:
    parts = path.replace("/", "\\").split("\\")
    return len(parts) == 3 and parts[1].lower() == "users"


def _guess_mac(windows: str, win_home: str, mac_home: Path) -> str:
    from cursor_mac_migrate.paths import normalize_windows_path, to_posix

    win = normalize_windows_path(windows)
    home = normalize_windows_path(win_home)
    if win.lower().startswith(home.lower()):
        suffix = win[len(home) :].replace("\\", "/")
        return to_posix(str(mac_home) + suffix)
    slug = win.replace("\\", "_")
    return f"FILL_IN_MAC_PATH_FOR_{slug}"
