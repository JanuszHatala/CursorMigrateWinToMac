from pathlib import Path

from cursor_mac_migrate.paths import (
    PathRewriter,
    extract_windows_paths,
    mac_to_file_uri,
    project_dir_name,
    replacement_pairs,
    windows_to_file_uri,
)
from cursor_mac_migrate.workspace_ids import compute_code_workspace_id


def test_replacement_covers_uri_and_backslash():
    pairs = replacement_pairs(r"C:\Users\Alice\dev", "/Users/alice/dev")
    rewriter = PathRewriter(pairs)
    assert rewriter.rewrite_string(r"C:\Users\Alice\dev\api\main.py") == "/Users/alice/dev/api/main.py"
    assert rewriter.rewrite_string("C:/Users/Alice/dev/api") == "/Users/alice/dev/api"
    uri = windows_to_file_uri(r"C:\Users\Alice\dev")
    assert rewriter.rewrite_string(uri) == mac_to_file_uri("/Users/alice/dev")
    nested = r"C:\\Users\\Alice\\dev\\api"
    assert "Users/alice/dev" in rewriter.rewrite_string(nested).replace("\\", "/")


def test_drive_letter_forms_and_renamed_folder():
    pairs = replacement_pairs(r"C:\DevWorkspaces", "/Users/jh/DevWorkspaces")
    pairs += replacement_pairs(
        r"C:\DevWorkspaces\acme\syncvault",
        "/Users/jh/DevWorkspaces/acme/sync-vault",
    )
    rewriter = PathRewriter(pairs)
    mac_repo = "/Users/jh/DevWorkspaces/acme/portal"
    assert rewriter.rewrite_string("c:/DevWorkspaces/acme/portal") == mac_repo
    assert rewriter.rewrite_string("C:/DevWorkspaces/acme/portal") == mac_repo
    assert rewriter.rewrite_string("/c:/DevWorkspaces/acme/portal") == mac_repo
    assert rewriter.rewrite_string("/C:/DevWorkspaces/acme/portal") == mac_repo
    assert (
        rewriter.rewrite_string("c:/DevWorkspaces/acme/syncvault")
        == "/Users/jh/DevWorkspaces/acme/sync-vault"
    )


def test_longest_prefix_wins():
    pairs = replacement_pairs(r"C:\Users\Alice", "/Users/alice")
    pairs += replacement_pairs(r"C:\Users\Alice\dev", "/Volumes/work/dev")
    rewriter = PathRewriter(pairs)
    assert rewriter.rewrite_string(r"C:\Users\Alice\dev\api") == "/Volumes/work/dev/api"
    assert rewriter.rewrite_string(r"C:\Users\Alice\Documents\x") == "/Users/alice/Documents/x"


def test_python_exe_becomes_mac_python():
    pairs = replacement_pairs(r"C:\Users\Alice", "/Users/alice")
    rewriter = PathRewriter(pairs, python="/opt/homebrew/bin/python3")
    assert (
        rewriter.rewrite_string(r"C:\Users\Alice\AppData\Local\Programs\Python\Python312\python.exe")
        == "/opt/homebrew/bin/python3"
    )


def test_intellij_exe():
    rewriter = PathRewriter([], intellij="/Applications/IntelliJ IDEA.app")
    assert (
        rewriter.rewrite_string(r"C:\Program Files\JetBrains\IntelliJ IDEA 2024.3\bin\idea64.exe")
        == "/Applications/IntelliJ IDEA.app"
    )


def test_extract_and_project_dir_name():
    blob = 'folder: file:///c%3A/Users/Alice/dev/api'
    found = extract_windows_paths(blob)
    assert any(item.endswith(r"Users\Alice\dev\api") or item.endswith("Users\\Alice\\dev\\api") for item in found)
    assert project_dir_name(r"C:\Users\Alice\dev") == "C-Users-Alice-dev"
    assert project_dir_name("/Users/alice/dev") == "Users-alice-dev"


def test_code_workspace_id_is_lowercase_md5(tmp_path: Path):
    file = tmp_path / "Platform.CODE-workspace"
    file.write_text("{}", encoding="utf-8")
    result = compute_code_workspace_id(file)
    import hashlib

    expected = hashlib.md5(file.absolute().as_posix().lower().encode()).hexdigest()
    assert result.workspace_id == expected


def test_rewrite_workspace_identifier_id():
    pairs = replacement_pairs(r"C:\Users\Alice\dev", "/Users/alice/dev")
    rewriter = PathRewriter(pairs, extra_id_map={"aaaabbbbccccddddeeeeffffaaaabbbb": "0123456789abcdef0123456789abcdef"})
    payload = {
        "allComposers": [
            {
                "composerId": "chat-1",
                "workspaceIdentifier": {
                    "id": "aaaabbbbccccddddeeeeffffaaaabbbb",
                    "uri": {
                        "fsPath": r"C:\Users\Alice\dev",
                        "scheme": "file",
                        "external": windows_to_file_uri(r"C:\Users\Alice\dev"),
                    },
                },
            }
        ]
    }
    out = rewriter.rewrite_obj(payload)
    ident = out["allComposers"][0]["workspaceIdentifier"]
    assert ident["id"] == "0123456789abcdef0123456789abcdef"
    assert ident["uri"]["fsPath"] == "/Users/alice/dev"
