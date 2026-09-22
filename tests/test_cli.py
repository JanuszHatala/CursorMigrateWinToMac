import pytest

from cursor_mac_migrate.cli import main
from cursor_mac_migrate.lock import is_cursor_editor_process


def test_macos_cursor_ui_service_is_not_the_editor():
    assert is_cursor_editor_process("/System/Library/PrivateFrameworks/TextInputUIMacHelper.framework/Versions/A/XPCServices/CursorUIViewService.xpc/Contents/MacOS/CursorUIViewService") is False
    assert is_cursor_editor_process("/Applications/Cursor.app/Contents/MacOS/Cursor") is True


def test_help_exits_zero():
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
