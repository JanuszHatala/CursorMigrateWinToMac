"""Refuse to touch Cursor data while the app is running."""

from __future__ import annotations

import subprocess
from pathlib import Path


def is_cursor_editor_process(command: str) -> bool:
    """True only for the Cursor editor, not the macOS CursorUIViewService."""
    if "cursor_mac_migrate" in command or "pgrep" in command:
        return False
    if "CursorUIViewService" in command:
        return False
    if "/System/Library/" in command:
        return False
    return "Cursor.app" in command or "Cursor Helper" in command


def cursor_pids() -> list[str]:
    try:
        out = subprocess.check_output(
            ["pgrep", "-if", "Cursor.app"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    pids = [line.strip() for line in out.splitlines() if line.strip()]
    filtered: list[str] = []
    for pid in pids:
        try:
            cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\x00", b" ").decode()
        except OSError:
            try:
                cmd = subprocess.check_output(
                    ["ps", "-p", pid, "-o", "command="],
                    text=True,
                    stderr=subprocess.DEVNULL,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        if is_cursor_editor_process(cmd):
            filtered.append(pid)
    return filtered


def assert_cursor_closed(*, allow_running: bool = False) -> None:
    if allow_running:
        return
    pids = cursor_pids()
    if pids:
        raise SystemExit(
            "Cursor is still running (pids: "
            + ", ".join(pids)
            + "). Quit it with Cmd+Q, confirm in Activity Monitor, then retry."
        )


def db_looks_locked(db_path: Path) -> bool:
    try:
        out = subprocess.check_output(
            ["lsof", str(db_path)],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return bool(out.strip())
