# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

if sys.platform != "win32":
    print("WinAssocGuard is Windows-only.")
    sys.exit(1)

from winassocguard.app import WinAssocGuardApp


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    app = WinAssocGuardApp(base_dir)
    app.run()


if __name__ == "__main__":
    main()
