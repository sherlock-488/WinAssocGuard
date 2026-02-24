# WinAssocGuard

Windows file association guard tool.  
It monitors selected file extensions and restores their saved baseline app when associations are changed.

## Highlights

- Single-window control panel (Guard / Logs / Settings tabs)
- Baseline editing via app picker (advanced manual ProgId is still available)
- Background monitoring with optional auto-restore
- Tray app with only two menu items:
  - Open control panel
  - Switch language
- Bilingual UI (Chinese / English)
- Per-user startup toggle

## Platform

- Windows 10 / 11
- Python 3.9+

## Install and run (source)

```powershell
cd WinAssocGuard
pip install -r requirements.txt
python main.py
```

## How it works

For Windows 8+ `UserChoice`, direct write is hash-protected.  
This project uses:

1. Set `HKCU\Software\Classes\.ext` default to baseline ProgId
2. Delete `UserChoice` for that extension
3. Broadcast association changed

This works in many real cases, but some systems/apps may still override aggressively.

## Typical usage

1. Add extensions to guard (or import common extensions)
2. Double-click baseline column for an extension and pick the app baseline
3. Keep "Guard enabled" on in Settings
4. Optionally turn on startup in Settings

## Project structure

- `main.py`: entry point
- `winassocguard/app.py`: app orchestration, monitor loop, tray wiring
- `winassocguard/ui.py`: tkinter control panel and dialogs
- `winassocguard/registry.py`: registry read/write and restore logic
- `winassocguard/config.py`: config load/save
- `winassocguard/tray.py`: tray menu
- `winassocguard/i18n.py`: translations

## Build executable

```powershell
pip install pyinstaller
pyinstaller --noconsole --onefile --name WinAssocGuard --clean main.py
```

Output:

- `dist/WinAssocGuard.exe`

## GitHub release flow

This repo includes GitHub Actions workflows:

- CI workflow: compile check on push/PR
- Release workflow: on tag `v*`, build `WinAssocGuard.exe` and publish to GitHub Releases

Suggested release steps:

1. Update `CHANGELOG.md`
2. Commit and push
3. Tag and push tag, e.g. `v0.1.0`
4. Download built artifact from Releases

## Notes for maintainers

- `config.json` is ignored by git (local runtime file)
- If you ship to public users, code signing is strongly recommended to reduce SmartScreen warnings

## License

MIT - see `LICENSE`.

