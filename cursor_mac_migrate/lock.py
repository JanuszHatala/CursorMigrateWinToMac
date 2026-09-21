"""Refuse to touch Cursor data while the app is running."""

from __future__ import annotations

import subprocess
from pathlib import Path


def cursor_pids() -> list[str]:
    try:
        out = subprocess.check_output(
            ["pgrep", "-if", "Cursor"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    pids = [line.strip() for line in out.splitlines() if line.strip()]
    # pgrep -if matches this Python command if it contains "Cursor" in argv.
    self = str(Path(__file__))
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
                filtered.append(pid)
                continue
        if "cursor_mac_migrate" in cmd or "pgrep" in cmd:
            continue
        if "Cursor" in cmd or "Cursor Helper" in cmd:
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
