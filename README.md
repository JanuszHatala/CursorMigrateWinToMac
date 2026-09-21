# Move Cursor from the Windows PC to this Mac

Your Mac user is `jh`. Your Windows user is `janusz`. Python on this Mac is `/opt/homebrew/bin/python3`.

The tool rewrites every Windows path that starts with `C:\Users\janusz` so the same ending is used under `/Users/jh`.

Example: `C:\Users\janusz\Projects\api` becomes `/Users/jh/Projects/api`.

You do not paste project folders. You do not edit a list. One command walks the copied Cursor files.

This only works when the project on the Mac is in the same place relative to your home folder. If Windows had the project in `C:\Users\janusz\Projects\api`, the Mac copy must be `/Users/jh/Projects/api`. Projects that are not there are written to a short file on the Desktop. They are not printed as a flood in Terminal.

## Do this

1. Quit Cursor. Click **Cursor** in the top menu bar, then **Quit Cursor**.

2. Open Terminal. Press the **Command** key and the **Space** bar together. Type `Terminal`. Press Return.

3. Go to the folder that contains `migrate.sh`. If you put that folder on the Desktop and it is named `cursor-mac-migrate`, paste:

```bash
cd "$HOME/Desktop/cursor-mac-migrate"
ls
```

`ls` must show `migrate.sh`. If the folder has a different name, use that name instead of `cursor-mac-migrate`.

4. Turn on the tool (you already did this once if a prompt starting with `(.venv)` is showing):

```bash
source .venv/bin/activate
```

If that says no such file, paste this once:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

5. Preview. This does not change files. It can sit quietly for a minute, then print a short summary:

```bash
python3 -m cursor_mac_migrate auto --windows-home 'C:\Users\janusz' --mac-home /Users/jh
```

6. Read the three files on the Desktop (double-click them, they open in TextEdit):

- `cursor-migrate-ready.txt` lists projects that already exist at the matching Mac path. Those chats can be attached.
- `cursor-migrate-missing.txt` lists projects whose Mac folder is not at the matching path. Copy or clone that project so `C:\Users\janusz\some\folder` exists as `/Users/jh/some/folder`, then run the command again.
- `cursor-migrate-outside-home.txt` lists anything that was not under `C:\Users\janusz` (another drive, for example `D:\`). Send me that file if it is not empty. The home-folder command cannot guess those.

7. Apply. Cursor must still be quit.

```bash
python3 -m cursor_mac_migrate auto --windows-home 'C:\Users\janusz' --mac-home /Users/jh --apply
```

Python settings that pointed at `python.exe` are changed to `/opt/homebrew/bin/python3`.

If IntelliJ IDEA is installed in the Applications folder, the tool finds `IntelliJ IDEA.app` by itself and replaces `idea64.exe`. If the summary says IntelliJ was not found, install it, then run the apply command again. You do not type the IntelliJ path.

8. Open Cursor. Use **File → Open Folder** for a project, or **File → Open Workspace from File** for a file whose name ends in `.code-workspace`. The chat from Windows should be in the list on the left.

Skills copied into `/Users/jh/.cursor/skills` are already on the Mac. The summary prints how many it found. Open **Customize → Skills** to see them.

## If Terminal floods again

Do not use `scan`. Use the `auto` command above. It writes the long lists to the Desktop and prints only counts.
