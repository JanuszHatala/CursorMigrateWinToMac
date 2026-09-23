import gzip
import json
import sqlite3
from pathlib import Path

from cursor_mac_migrate.apply import apply_map, rewrite_stored_paths
from cursor_mac_migrate.mapping import PathMap, RootMap
from cursor_mac_migrate.sidecars import rewrite_sidecars, sidecar_roots


def test_glass_workspace_file_gets_mac_folder_path(tmp_path: Path):
    user_dir = tmp_path / "Cursor" / "User"
    user_dir.mkdir(parents=True)
    glass = tmp_path / "Cursor" / "glassMultiRootWorkspaces"
    glass.mkdir()
    workspace = glass / "acme.code-workspace"
    workspace.write_text(
        json.dumps({"folders": [{"path": "c:/DevWorkspaces/acme"}, {"name": "acme"}]}),
        encoding="utf-8",
    )
    mac_root = tmp_path / "mac-dev"
    path_map = PathMap(
        roots=[RootMap(r"C:\DevWorkspaces", str(mac_root), "folder")],
        user_dir=user_dir,
        dot_cursor=tmp_path / ".cursor",
    )

    changed = rewrite_sidecars(user_dir, path_map.rewriter())

    data = json.loads(workspace.read_text(encoding="utf-8"))
    assert data["folders"][0]["path"] == f"{mac_root}/acme"
    assert workspace in changed
    assert sidecar_roots(user_dir) == [glass]


def test_apply_rewrites_glass_file_from_prefix_even_when_chat_map_is_narrow(tmp_path: Path):
    user_dir = tmp_path / "Cursor" / "User"
    (user_dir / "globalStorage").mkdir(parents=True)
    glass = tmp_path / "Cursor" / "glassMultiRootWorkspaces"
    glass.mkdir()
    workspace = glass / "acme.code-workspace"
    workspace.write_text(
        json.dumps({"folders": [{"path": "c:/DevWorkspaces/acme"}]}),
        encoding="utf-8",
    )
    mac_root = tmp_path / "mac-dev"
    narrow = PathMap(roots=[], user_dir=user_dir, dot_cursor=tmp_path / ".cursor")
    apply_map(
        narrow,
        skip_missing=True,
        rewrite_roots=[RootMap(r"C:\DevWorkspaces", str(mac_root), "folder")],
    )
    data = json.loads(workspace.read_text(encoding="utf-8"))
    assert data["folders"][0]["path"] == f"{mac_root}/acme"


def test_gzipped_sqlite_and_repo_workspace_file(tmp_path: Path):
    user_dir = tmp_path / "Cursor" / "User"
    (user_dir / "globalStorage").mkdir(parents=True)
    db = user_dir / "globalStorage" / "state.vscdb"
    payload = json.dumps(
        {
            "path": "/C:/DevWorkspaces/acme/portal",
            "external": "file:///c%3A/DevWorkspaces/acme/portal",
            "fsPath": "c:/DevWorkspaces/acme/syncvault",
        }
    )
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value BLOB)")
    conn.execute("CREATE TABLE GlassState (id INTEGER PRIMARY KEY, payload TEXT)")
    conn.execute(
        "INSERT INTO ItemTable(key, value) VALUES (?, ?)",
        ("cursor/glass.additionalProjects", gzip.compress(payload.encode())),
    )
    conn.execute(
        "INSERT INTO GlassState(payload) VALUES (?)",
        ("C:/DevWorkspaces/acme/portal",),
    )
    conn.commit()
    conn.close()
    mac_dev = tmp_path / "mac-dev"
    (mac_dev / "acme").mkdir(parents=True)
    repo_ws = mac_dev / "acme" / "portal.code-workspace"
    repo_ws.write_text(
        json.dumps({"folders": [{"path": "c:/DevWorkspaces/acme/portal"}]}),
        encoding="utf-8",
    )
    path_map = PathMap(
        roots=[
            RootMap(r"C:\DevWorkspaces", str(mac_dev), "folder"),
            RootMap(
                r"C:\DevWorkspaces\acme\syncvault",
                str(mac_dev / "acme" / "sync-vault"),
                "folder",
            ),
        ],
        user_dir=user_dir,
        dot_cursor=tmp_path / ".cursor",
    )
    rewrite_stored_paths(path_map)
    conn = sqlite3.connect(db)
    raw = conn.execute(
        "SELECT value FROM ItemTable WHERE key='cursor/glass.additionalProjects'"
    ).fetchone()[0]
    extra = conn.execute("SELECT payload FROM GlassState").fetchone()[0]
    conn.close()
    data = json.loads(gzip.decompress(raw).decode())
    assert data["path"] == f"{mac_dev}/acme/portal"
    assert data["fsPath"] == f"{mac_dev}/acme/sync-vault"
    assert extra == f"{mac_dev}/acme/portal"
    on_disk = json.loads(repo_ws.read_text(encoding="utf-8"))
    assert on_disk["folders"][0]["path"] == f"{mac_dev}/acme/portal"
