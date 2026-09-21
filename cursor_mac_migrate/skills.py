"""Skills and ~/.cursor/projects helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

from cursor_mac_migrate.paths import PathRewriter, project_dir_name


def list_skills(dot_cursor: Path) -> list[Path]:
    root = dot_cursor / "skills"
    if not root.is_dir():
        return []
    return sorted({path.parent for path in root.rglob("SKILL.md")})


def rename_project_dirs(
    dot_cursor: Path,
    rewriter: PathRewriter,
    windows_paths: list[str],
    *,
    dry_run: bool = False,
) -> list[tuple[str, str, str]]:
    """Rename ~/.cursor/projects/<windows-encoded> to the macOS encoded name."""
    root = dot_cursor / "projects"
    if not root.is_dir():
        return []
    changes: list[tuple[str, str, str]] = []
    existing = {p.name: p for p in root.iterdir() if p.is_dir()}
    for windows in windows_paths:
        old_name = project_dir_name(windows)
        mac = rewriter.rewrite_string(windows)
        if mac == windows:
            continue
        new_name = project_dir_name(mac)
        if old_name == new_name:
            continue
        src = existing.get(old_name)
        if src is None:
            continue
        dest = root / new_name
        if dest.exists():
            changes.append((old_name, new_name, "collision"))
            continue
        if not dry_run:
            shutil.move(str(src), str(dest))
            existing.pop(old_name, None)
            existing[new_name] = dest
        changes.append((old_name, new_name, "renamed"))
    return changes
