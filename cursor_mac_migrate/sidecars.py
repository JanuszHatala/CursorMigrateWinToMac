"""Rewrite Windows paths in Cursor files that sit beside the User folder.

Named multi-folder workspaces (the Add Folders dialog) are stored as
.code-workspace files under glassMultiRootWorkspaces, next to User, not inside it.
"""

from __future__ import annotations

from pathlib import Path

from cursor_mac_migrate.files_rewrite import SKIP_DIR_NAMES, iter_text_files, rewrite_file
from cursor_mac_migrate.mapping import PathMap
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


def rewrite_workspace_files_on_mac(
    path_map: PathMap,
    rewriter: PathRewriter,
    *,
    dry_run: bool = False,
) -> list[Path]:
    """Rewrite .code-workspace files that live inside the copied repos."""
    changed: list[Path] = []
    seen: set[Path] = set()
    skip = set(SKIP_DIR_NAMES) | {".git", "node_modules", ".venv", "venv"}
    for root in path_map.roots:
        base = Path(root.mac)
        candidates: list[Path] = []
        if base.is_file() and base.suffix.lower() == ".code-workspace":
            candidates.append(base)
        elif base.is_dir():
            for path in base.rglob("*.code-workspace"):
                if any(part in skip for part in path.parts):
                    continue
                try:
                    depth = len(path.relative_to(base).parts)
                except ValueError:
                    continue
                if depth > 6:
                    continue
                candidates.append(path)
        for path in candidates:
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            stats = rewrite_file(path, rewriter, dry_run=dry_run)
            if stats.changed:
                changed.append(path)
    return changed
