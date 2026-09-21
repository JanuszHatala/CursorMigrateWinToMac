# Move Cursor from the Windows PC to this Mac

The project folders on Windows are under `C:\DevWorkspaces`, not under `C:\Users\janusz`. On the Mac that same tree is `/Users/jh/DevWorkspaces`.

So `C:\DevWorkspaces\timebook` becomes `/Users/jh/DevWorkspaces/timebook`.
And `C:\DevWorkspaces\timebook-jh\automate-mvn-upgrade\repos\...` becomes `/Users/jh/DevWorkspaces/timebook-jh/automate-mvn-upgrade/repos/...`.

Anything that really did live under `C:\Users\janusz` is rewritten under `/Users/jh`. Python `.exe` paths become `/opt/homebrew/bin/python3`.

## Where the tool is

It is not on the Windows PC. There is no `C:\` folder for it. It was written in this chat's project, on a cloud machine, not on your disk.

The folder you need contains these names:

- `migrate.sh`
- `README.md`
- `cursor_mac_migrate` (a folder)
- `pyproject.toml`

Copy that whole folder, not one file inside it. Put the copy on the Mac Desktop.

How to get it there: in this chat, download or export the project files (the file list for this agent). If you get a zip, unzip it. Move the unzipped folder onto the Mac Desktop. In Finder it should sit on the Desktop, and inside it you must see `migrate.sh`.

## On the Mac

1. Quit Cursor. Menu bar: **Cursor → Quit Cursor**.

2. Press **Command** and **Space**, type `Terminal`, press Return.

3. Go into the folder you just put on the Desktop. If Finder shows that folder as `cursor-mac-migrate`:

```bash
cd "$HOME/Desktop/cursor-mac-migrate"
ls
```

`ls` must print `migrate.sh`. If the folder name is different, use the name you see on the Desktop instead of `cursor-mac-migrate`.

4. Paste this once:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

5. Preview. It does not change files. It stays quiet, then prints a short summary:

```bash
python3 -m cursor_mac_migrate auto --windows-home 'C:\Users\janusz' --mac-home /Users/jh --also 'C:\DevWorkspaces=/Users/jh/DevWorkspaces'
```

6. On the Desktop, open `cursor-migrate-missing.txt` if the summary says some projects are missing. Those are Windows paths whose Mac folder was not found at the matching place under `/Users/jh/DevWorkspaces`. Also open `cursor-migrate-outside-home.txt` if it is not empty, and send me that file. Those paths are outside both `C:\DevWorkspaces` and `C:\Users\janusz`.

7. Apply. Cursor must still be quit:

```bash
python3 -m cursor_mac_migrate auto --windows-home 'C:\Users\janusz' --mac-home /Users/jh --also 'C:\DevWorkspaces=/Users/jh/DevWorkspaces' --apply
```

8. Open Cursor. **File → Open Folder** and choose a folder under `/Users/jh/DevWorkspaces`, or **File → Open Workspace from File** for a `.code-workspace`. The Windows chat should be in the list.
