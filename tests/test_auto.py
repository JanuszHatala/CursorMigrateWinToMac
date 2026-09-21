from cursor_mac_migrate.auto import build_auto_plan, translate_home
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
