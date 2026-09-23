import json
from pathlib import Path

from cursor_mac_migrate.apply import apply_map
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
