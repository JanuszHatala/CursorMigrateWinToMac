import pytest

from cursor_mac_migrate.cli import main
from cursor_mac_migrate.lock import is_cursor_editor_process


def test_help_exits_zero():
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
