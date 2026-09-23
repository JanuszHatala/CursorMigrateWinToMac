"""Apply the full Windows → macOS remap."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from cursor_mac_migrate.detect import scan_tree
from cursor_mac_migrate.extensions import iter_extensions
from cursor_mac_migrate.files_rewrite import iter_text_files, rewrite_file
from cursor_mac_migrate.mapping import PathMap, RootMap, missing_mac_targets
from cursor_mac_migrate.sidecars import rewrite_sidecars
from cursor_mac_migrate.skills import list_skills, rename_project_dirs
from cursor_mac_migrate.sqlite_rewrite import checkpoint_and_copy, rewrite_db
from cursor_mac_migrate.workspace_relink import RelinkResult, relink_workspaces


@dataclass
class ApplyReport:
    backup_dir: Path | None
    relink: RelinkResult
    sqlite: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)


def apply_map(
    path_map: PathMap,
    *,
    dry_run: bool = False,
    skip_missing: bool = False,
    rewrite_roots: list[RootMap] | None = None,
) -> ApplyReport:
    user_dir = path_map.user_dir
    dot_cursor = path_map.dot_cursor
    assert user_dir is not None and dot_cursor is not None

    missing = missing_mac_targets(path_map)
    warnings = list(missing)
    if missing and not skip_missing and not dry_run:
        raise SystemExit(
            "These Mac paths do not exist yet:\n  - "
            + "\n  - ".join(missing)
            + "\n\nCreate/clone them, edit path-map.json, or pass --allow-missing to continue."
        )

    backup_dir = None
    if not dry_run:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_dir = user_dir.parent / f"User.mac-migrate-backup-{stamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

    pre_scan = scan_tree(user_dir, dot_cursor)
    original_dbs = _db_paths(user_dir)
    if backup_dir is not None:
        for db in original_dbs:
            checkpoint_and_copy(db, backup_dir / "sqlite" / _backup_name(user_dir, db))

    relink = relink_workspaces(user_dir, path_map, dry_run=dry_run)
    rewriter = path_map.rewriter(relink.id_map)
    sidecar_rewriter = _string_rewriter(path_map, rewrite_roots, relink.id_map)

    report = ApplyReport(backup_dir=backup_dir, relink=relink, warnings=warnings)
    report.skills = [str(path) for path in list_skills(dot_cursor)]

    dbs = _db_paths(user_dir)
    for db in dbs:
        stats = rewrite_db(db, rewriter, dry_run=dry_run)
        if stats.rows_changed:
            report.sqlite.append(
                f"{db}: {stats.rows_changed} rows rewritten ({stats.rows_seen} scanned)"
            )

    for path in iter_text_files(user_dir) + iter_text_files(dot_cursor):
        stats = rewrite_file(path, rewriter, dry_run=dry_run)
        if stats.changed:
            report.files.append(str(path))

    for path in rewrite_sidecars(user_dir, sidecar_rewriter, dry_run=dry_run):
        report.files.append(str(path))

    windows_paths = list(pre_scan.windows_paths) or _windows_from_map(path_map)
    for old, new, status in rename_project_dirs(
        dot_cursor, rewriter, windows_paths, dry_run=dry_run
    ):
        report.projects.append(f"{old} → {new} ({status})")

    # Rewrite .code-workspace files that already live at their Mac paths.
    for root in path_map.roots:
        if root.kind != "workspace":
            continue
        target = Path(root.mac)
        if target.exists():
            stats = rewrite_file(target, rewriter, dry_run=dry_run)
            if stats.changed:
                report.files.append(str(target))
        elif not dry_run:
            report.warnings.append(f"workspace file not on disk yet: {root.mac}")

    native = [ext for ext in iter_extensions(dot_cursor) if ext.needs_reinstall]
    for ext in native:
        report.warnings.append(
            f"Reinstall extension on Mac: {ext.ext_id} ({ext.reason})"
        )
    return report


def rewrite_stored_paths(path_map: PathMap, *, dry_run: bool = False) -> list[str]:
    """Rewrite Windows paths in profile files without moving workspaceStorage.

    Use this after a migration when a named workspace still shows a Windows folder.
    """
    user_dir = path_map.user_dir
    dot_cursor = path_map.dot_cursor
    assert user_dir is not None and dot_cursor is not None
    rewriter = path_map.rewriter()
    changed: list[str] = []
    for path in rewrite_sidecars(user_dir, rewriter, dry_run=dry_run):
        changed.append(str(path))
    for path in iter_text_files(user_dir) + iter_text_files(dot_cursor):
        stats = rewrite_file(path, rewriter, dry_run=dry_run)
        if stats.changed:
            changed.append(str(path))
    for db in _db_paths(user_dir):
        stats = rewrite_db(db, rewriter, dry_run=dry_run)
        if stats.rows_changed:
            changed.append(f"{db} ({stats.rows_changed} rows)")
    return changed


def _string_rewriter(path_map: PathMap, rewrite_roots: list[RootMap] | None, id_map: dict[str, str]):
    if not rewrite_roots:
        return path_map.rewriter(id_map)
    broader = PathMap(
        roots=[*rewrite_roots, *path_map.roots],
        python=path_map.python,
        intellij=path_map.intellij,
        user_dir=path_map.user_dir,
        dot_cursor=path_map.dot_cursor,
    )
    return broader.rewriter(id_map)


def _db_paths(user_dir: Path) -> list[Path]:
    paths: list[Path] = []
    global_db = user_dir / "globalStorage" / "state.vscdb"
    if global_db.exists():
        paths.append(global_db)
    storage = user_dir / "workspaceStorage"
    if storage.is_dir():
        paths.extend(sorted(storage.glob("*/state.vscdb")))
    return paths


def _backup_name(user_dir: Path, db: Path) -> Path:
    try:
        rel = db.relative_to(user_dir)
    except ValueError:
        rel = Path(db.name)
    return rel


def _windows_from_map(path_map: PathMap) -> list[str]:
    return [root.windows for root in path_map.roots]


def write_report(report: ApplyReport, path: Path) -> None:
    payload = {
        "backup_dir": str(report.backup_dir) if report.backup_dir else None,
        "relink": [
            {
                "old_id": item.old_id,
                "new_id": item.new_id,
                "windows_uri": item.windows_uri,
                "mac_path": item.mac_path,
                "kind": item.kind,
                "status": item.status,
                "detail": item.detail,
            }
            for item in report.relink.items
        ],
        "id_map": report.relink.id_map,
        "sqlite": report.sqlite,
        "files": report.files,
        "projects": report.projects,
        "skills": report.skills,
        "warnings": report.warnings,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
