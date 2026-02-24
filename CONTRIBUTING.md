# Contributing

Thanks for contributing.

## Development setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Pull request checklist

- Keep changes focused and small
- Run compile check before opening PR:

```powershell
python -m compileall winassocguard main.py
```

- Update `CHANGELOG.md` for user-visible changes
- Include screenshots for UI changes when possible

## Style notes

- Keep Windows compatibility
- Preserve Chinese/English i18n keys together
- Avoid destructive behavior on registry writes

