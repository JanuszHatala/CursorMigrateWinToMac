import json
import sqlite3
from pathlib import Path

from cursor_mac_migrate.apply import apply_map
from cursor_mac_migrate.mapping import PathMap, RootMap
from cursor_mac_migrate.sqlite_rewrite import rewrite_db
from cursor_mac_migrate.workspace_ids import compute_code_workspace_id, compute_folder_workspace_id
from cursor_mac_migrate.workspace_relink import relink_workspaces
from cursor_mac_migrate.paths import PathRewriter, replacement_pairs, windows_to_file_uri


def _make_db(path: Path, items: dict[str, str]) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT)")
    conn.executemany("INSERT INTO ItemTable(key, value) VALUES (?, ?)", items.items())
    conn.commit()
    conn.close()


def test_sqlite_rewrites_composer_headers(tmp_path: Path):
    db = tmp_path / "state.vscdb"
    headers = {
        "allComposers": [
            {
                "composerId": "abc",
                "workspaceIdentifier": {
                    "id": "oldidoldidoldidoldidoldidoldidoldi",
                    "uri": {"fsPath": r"C:\Users\Alice\dev\api"},
                },
            }
        ]
    }
    _make_db(db, {"composer.composerHeaders": json.dumps(headers)})
    rewriter = PathRewriter(
        replacement_pairs(r"C:\Users\Alice\dev", "/Users/alice/dev"),
        extra_id_map={"oldidoldidoldidoldidoldidoldidoldi": "newidnewidnewidnewidnewidnewidnewi"},
    )
    stats = rewrite_db(db, rewriter)
    assert stats.rows_changed == 1
    conn = sqlite3.connect(db)
    value = conn.execute(
        "SELECT value FROM ItemTable WHERE key='composer.composerHeaders'"
    ).fetchone()[0]
    conn.close()
    data = json.loads(value)
    ident = data["allComposers"][0]["workspaceIdentifier"]
    assert ident["uri"]["fsPath"] == "/Users/alice/dev/api"
    assert ident["id"].startswith("newid")


def test_relink_multi_root_workspace(tmp_path: Path):
    mac_ws = tmp_path / "platform.code-workspace"
    mac_ws.write_text(
        json.dumps(
            {
                "folders": [
                    {"path": r"C:\\Users\\Alice\\dev\\api"},
                    {"path": r"C:\\Users\\Alice\\dev\\web"},
                ]
            }
        ),
        encoding="utf-8",
    )
    user_dir = tmp_path / "User"
    old_id = "windowsidwindowsidwindowsidwinid"
    storage = user_dir / "workspaceStorage" / old_id
    storage.mkdir(parents=True)
    (storage / "workspace.json").write_text(
        json.dumps({"workspace": windows_to_file_uri(r"C:\Users\Alice\dev\platform.code-workspace")}),
        encoding="utf-8",
    )
    path_map = PathMap(
        roots=[
            RootMap(r"C:\Users\Alice\dev", str(tmp_path), "folder"),
            RootMap(
                r"C:\Users\Alice\dev\platform.code-workspace",
                str(mac_ws),
                "workspace",
            ),
        ],
        user_dir=user_dir,
        dot_cursor=tmp_path / ".cursor",
    )
    result = relink_workspaces(user_dir, path_map)
    expected = compute_code_workspace_id(mac_ws).workspace_id
    assert result.id_map[old_id] == expected
    new_meta = json.loads(
        (user_dir / "workspaceStorage" / expected / "workspace.json").read_text()
    )
    assert new_meta["workspace"].endswith("platform.code-workspace")
    assert "file://" in new_meta["workspace"]
    assert "C:" not in new_meta["workspace"]


def test_relink_folder_workspace(tmp_path: Path):
    repo = tmp_path / "api"
    repo.mkdir()
    user_dir = tmp_path / "User"
    old_id = "folderidfolderidfolderidfolderidxx"
    storage = user_dir / "workspaceStorage" / old_id
    storage.mkdir(parents=True)
    (storage / "state.vscdb").write_bytes(b"")
    (storage / "workspace.json").write_text(
        json.dumps({"folder": windows_to_file_uri(r"C:\Users\Alice\dev\api")}),
        encoding="utf-8",
    )
    path_map = PathMap(
        roots=[RootMap(r"C:\Users\Alice\dev", str(tmp_path), "folder")],
        user_dir=user_dir,
        dot_cursor=tmp_path / ".cursor",
    )
    result = relink_workspaces(user_dir, path_map)
    expected = compute_folder_workspace_id(repo).workspace_id
    assert result.id_map[old_id] == expected
    assert (user_dir / "workspaceStorage" / expected / "workspace.json").exists()


def test_apply_rewrites_skill_and_workspace_file(tmp_path: Path):
    repo_a = tmp_path / "api"
    repo_b = tmp_path / "web"
    repo_a.mkdir()
    repo_b.mkdir()
    mac_ws = tmp_path / "platform.code-workspace"
    mac_ws.write_text(
        json.dumps(
            {
                "folders": [
                    {"path": r"C:\\Users\\Alice\\dev\\api"},
                    {"path": r"C:\\Users\\Alice\\dev\\web"},
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    user_dir = tmp_path / "User"
    dot = tmp_path / ".cursor"
    old_id = "multiidmultiidmultiidmultiidmulti"
    storage = user_dir / "workspaceStorage" / old_id
    storage.mkdir(parents=True)
    (storage / "workspace.json").write_text(
        json.dumps(
            {"workspace": windows_to_file_uri(r"C:\Users\Alice\dev\platform.code-workspace")}
        ),
        encoding="utf-8",
    )
    headers = {
        "allComposers": [
            {
                "composerId": "session-from-windows",
                "name": "Continue me on Mac",
                "workspaceIdentifier": {
                    "id": old_id,
                    "uri": {
                        "fsPath": r"C:\Users\Alice\dev\platform.code-workspace",
                        "scheme": "file",
                    },
                },
            }
        ]
    }
    (user_dir / "globalStorage").mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(user_dir / "globalStorage" / "state.vscdb")
    conn.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute(
        "INSERT INTO ItemTable VALUES (?, ?)",
        ("composer.composerHeaders", json.dumps(headers)),
    )
    conn.commit()
    conn.close()

    (user_dir / "settings.json").write_text(
        json.dumps(
            {
                "python.defaultInterpreterPath": r"C:\Users\Alice\AppData\Local\Programs\Python\Python312\python.exe",
                "terminal.integrated.cwd": r"C:\Users\Alice\dev",
            }
        ),
        encoding="utf-8",
    )
    skill = dot / "skills" / "ship-it" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "Use the repo at C:\\Users\\Alice\\dev\\api\n", encoding="utf-8"
    )

    path_map = PathMap(
        roots=[
            RootMap(r"C:\Users\Alice\dev", str(tmp_path), "folder"),
            RootMap(
                r"C:\Users\Alice\dev\platform.code-workspace",
                str(mac_ws),
                "workspace",
            ),
            RootMap(r"C:\Users\Alice", str(tmp_path / "home"), "home"),
        ],
        python="/usr/bin/python3",
        user_dir=user_dir,
        dot_cursor=dot,
    )
    (tmp_path / "home").mkdir()
    report = apply_map(path_map, dry_run=False, skip_missing=True)
    assert any(item.status in {"renamed", "unchanged-id"} for item in report.relink.items)
    settings = json.loads((user_dir / "settings.json").read_text())
    assert settings["python.defaultInterpreterPath"] == "/usr/bin/python3"
    skill_text = skill.read_text()
    assert "C:\\Users" not in skill_text
    assert "api" in skill_text
    ws = json.loads(mac_ws.read_text())
    assert all("C:" not in folder["path"] for folder in ws["folders"])
    conn = sqlite3.connect(user_dir / "globalStorage" / "state.vscdb")
    headers_out = json.loads(
        conn.execute(
            "SELECT value FROM ItemTable WHERE key='composer.composerHeaders'"
        ).fetchone()[0]
    )
    ident = headers_out["allComposers"][0]["workspaceIdentifier"]
    assert ident["id"] == compute_code_workspace_id(mac_ws).workspace_id
    assert "platform.code-workspace" in ident["uri"]["fsPath"]
