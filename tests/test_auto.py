from cursor_mac_migrate.auto import build_auto_plan, path_map_for_apply, translate_home
from cursor_mac_migrate.detect import ScanResult


def test_translate_janusz_home_to_jh():
    assert (
        translate_home(r"C:\Users\janusz\Projects\api", r"C:\Users\janusz", "/Users/jh")
        == "/Users/jh/Projects/api"
    )
    assert (
        translate_home(
            r"C:\Users\janusz\source\platform.code-workspace",
            r"C:\Users\janusz",
            "/Users/jh",
        )
        == "/Users/jh/source/platform.code-workspace"
    )
    assert translate_home(r"D:\work\api", r"C:\Users\janusz", "/Users/jh") is None


def test_devworkspaces_is_rewritten_even_though_it_is_outside_the_user_folder(tmp_path):
    mac_repo = tmp_path / "DevWorkspaces" / "acme"
    mac_repo.mkdir(parents=True)
    scan = ScanResult()
    scan.workspace_uris = [
        ("abc", "folder", "file:///c%3A/DevWorkspaces/acme"),
        (
            "def",
            "folder",
            "file:///c%3A/DevWorkspaces/acme-lab/automate-mvn-upgrade/repos/demo",
        ),
    ]
    plan = build_auto_plan(
        scan,
        r"C:\Users\janusz",
        "/Users/jh",
        python="/opt/homebrew/bin/python3",
        intellij=None,
        extra_prefixes=[(r"C:\DevWorkspaces", str(tmp_path / "DevWorkspaces"))],
    )
    assert any(line.endswith(str(mac_repo)) or "/DevWorkspaces/acme" in line for line in plan.ready)
    assert len(plan.missing) == 1
    assert "automate-mvn-upgrade/repos/demo" in plan.missing[0]
    assert plan.outside_home == []


def test_syncvault_rename_suggested_when_mac_folder_uses_hyphens(tmp_path):
    dev = tmp_path / "DevWorkspaces"
    (dev / "sync-vault").mkdir(parents=True)
    scan = ScanResult()
    scan.workspace_uris = [
        ("abc", "folder", "file:///c%3A/DevWorkspaces/syncvault"),
        ("wt", "folder", "file:///c%3A/DevWorkspaces/acme/.cursor/worktrees/abc"),
        ("roam", "folder", "file:///c%3A/Users/janusz/AppData/Roaming/Cursor/Workspaces/abc"),
    ]
    plan = build_auto_plan(
        scan,
        r"C:\Users\janusz",
        "/Users/jh",
        python="/opt/homebrew/bin/python3",
        intellij=None,
        extra_prefixes=[(r"C:\DevWorkspaces", str(dev))],
    )
    assert plan.ready_pairs == []
    assert plan.rename_pairs == [(r"C:\DevWorkspaces\syncvault", str(dev / "sync-vault"))]
    assert any(line.startswith("[worktree]") for line in plan.keep)
    assert any(line.startswith("[cursor-internal]") for line in plan.keep)
    accepted = path_map_for_apply(plan, plan.rename_pairs, [])
    assert any(root.mac.endswith("sync-vault") for root in accepted.roots)
    assert all(
        not root.windows.lower().startswith(r"c:\devworkspaces")
        or root.windows.lower().endswith("syncvault")
        for root in accepted.roots
    )
    blocked = path_map_for_apply(plan, plan.rename_pairs, [r"C:\DevWorkspaces\syncvault"])
    assert blocked.roots == []


def test_auto_plan_uses_one_home_prefix(tmp_path):
    mac_repo = tmp_path / "Projects" / "api"
    mac_repo.mkdir(parents=True)
    scan = ScanResult()
    scan.workspace_uris = [
        ("abc", "folder", "file:///c%3A/Users/janusz/Projects/api"),
        ("def", "folder", "file:///c%3A/Users/janusz/Projects/missing"),
        ("ghi", "folder", "file:///d%3A/other/repo"),
    ]
    plan = build_auto_plan(
        scan,
        r"C:\Users\janusz",
        str(tmp_path),
        python="/opt/homebrew/bin/python3",
        intellij=None,
    )
    assert plan.path_map.roots[0].windows == r"C:\Users\janusz"
    assert plan.path_map.roots[0].mac == str(tmp_path)
    assert len(plan.ready) == 1
    assert "Projects/api" in plan.ready[0]
    assert len(plan.missing) == 1
    assert plan.outside_home == [r"D:\other\repo"]
