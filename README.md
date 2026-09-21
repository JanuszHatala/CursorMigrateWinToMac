# Move Cursor from the Windows PC to this Mac

Windows repositories live under `C:\DevWorkspaces`. On the Mac that same tree is `/Users/jh/DevWorkspaces`.

`C:\DevWorkspaces\timebook` becomes `/Users/jh/DevWorkspaces/timebook`.

Paths that really were under `C:\Users\janusz` become the same ending under `/Users/jh`. A Windows `python.exe` path becomes `/opt/homebrew/bin/python3`.

## Two different names

There is no folder named `cursor-mac-migrate`.

The folder you can see in the file list, `cursor_mac_migrate`, is the inner code. It does not contain `migrate.sh`. That is expected.

`migrate.sh` is in the parent folder, next to `cursor_mac_migrate`. The parent is the folder you copy. Open the parent and you see this list:

- `START-HERE.txt`
- `README.md`
- `pyproject.toml`
- `migrate.sh`
- `cursor_mac_migrate` (folder)

The command uses the inner name, with underscores: `python3 -m cursor_mac_migrate`.

This project is not stored on the Windows PC. Copy the parent folder (the one that contains the list above) onto the Mac Desktop.

## On the Mac

Quit Cursor: menu bar, **Cursor**, **Quit Cursor**.

Press **Command** and **Space**, type `Terminal`, press Return. Paste:

```bash
cd "$HOME/Desktop"
ls
```

`ls` prints the names on the Desktop. Use the name of the parent folder you copied (the one that contains `START-HERE.txt`). Paste it in place of `PARENT` below:

```bash
cd "$HOME/Desktop/PARENT"
ls
```

Stop if `ls` does not show `pyproject.toml` and `cursor_mac_migrate` together. If you only see files like `cli.py` and `auto.py`, you are inside `cursor_mac_migrate`. Paste `cd ..` and run `ls` again.

Then paste:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
python3 -m cursor_mac_migrate auto --windows-home 'C:\Users\janusz' --mac-home /Users/jh --also 'C:\DevWorkspaces=/Users/jh/DevWorkspaces'
```

That preview does not change Cursor. On the Desktop it writes:

- `cursor-migrate-ready.txt`: same folder name on the Mac. Safe to attach.
- `cursor-migrate-rename-suggested.txt`: different folder name, such as `wsgateway` and `ws-gateway`. Copy the lines you want into `cursor-migrate-rename.txt`.
- `cursor-migrate-keep.txt`: not copied, worktrees, and `AppData\Roaming\Cursor\Workspaces`. Left unchanged.
- `cursor-migrate-drop.txt`: one Windows path per line for chats you want to abandon. Also left unchanged.

Do not add `--apply` by itself. After you edit the rename and drop files, Cursor still quit:

```bash
python3 -m cursor_mac_migrate auto --windows-home 'C:\Users\janusz' --mac-home /Users/jh --also 'C:\DevWorkspaces=/Users/jh/DevWorkspaces' --renames "$HOME/Desktop/cursor-migrate-rename.txt" --drop "$HOME/Desktop/cursor-migrate-drop.txt" --apply
```

Only the ready list and the accepted renames are attached. To keep a missing repo, copy it to the Mac path on the right in `cursor-migrate-keep.txt`, run the preview again, then `--apply` again.
