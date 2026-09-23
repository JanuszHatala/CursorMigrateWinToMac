"""Rewrite Windows paths in Cursor files that sit beside the User folder.

Named multi-folder workspaces (the Add Folders dialog) are stored as
.code-workspace files under glassMultiRootWorkspaces, next to User, not inside it.
"""

from __future__ import annotations

from pathlib import Path

from cursor_mac_migrate.files_rewrite import iter_text_files, rewrite_file
from cursor_mac_migrate.paths import PathRewriter

SIDECAR_DIR_NAMES = ("glassMultiRootWorkspaces", "Workspaces")


def sidecar_roots(user_dir: Path) -> list[Path]:
    parent = user_dir.parent
    return [parent / name for name in SIDECAR_DIR_NAMES if (parent / name).is_dir()]


def rewrite_sidecars(
    user_dir: Path,
    rewriter: PathRewriter,
    *,
    dry_run: bool = False,
) -> list[Path]:
    changed: list[Path] = []
    for root in sidecar_roots(user_dir):
        for path in iter_text_files(root):
            stats = rewrite_file(path, rewriter, dry_run=dry_run)
            if stats.changed:
                changed.append(path)
    return changed
