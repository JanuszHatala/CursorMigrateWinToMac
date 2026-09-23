import pytest

from cursor_mac_migrate.cli import main
from cursor_mac_migrate.lock import is_cursor_editor_process
from cursor_mac_migrate.workdir import default_report_dir, tool_root


def test_macos_cursor_ui_service_is_not_the_editor():
    assert is_cursor_editor_process("/System/Library/PrivateFrameworks/TextInputUIMacHelper.framework/Versions/A/XPCServices/CursorUIViewService.xpc/Contents/MacOS/CursorUIViewService") is False
    assert is_cursor_editor_process("/Applications/Cursor.app/Contents/MacOS/Cursor") is True


def test_reports_live_next_to_the_tool_not_on_the_desktop():
    root = tool_root()
    assert (root / "pyproject.toml").is_file()
    assert default_report_dir() == root / "migrate-work"
    assert default_report_dir().name != "Desktop"


def test_help_exits_zero():
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
