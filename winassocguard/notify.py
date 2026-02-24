# -*- coding: utf-8 -*-
"""
Notification wrapper.

We use plyer to show native-ish Windows notifications.
If plyer fails (rare on some setups), we silently fall back to no-op.
"""

from __future__ import annotations

from typing import Optional


def notify(title: str, message: str, timeout: int = 5, app_name: Optional[str] = None) -> None:
    try:
        from plyer import notification  # type: ignore

        notification.notify(
            title=title,
            message=message,
            app_name=app_name or title,
            timeout=timeout,
        )
    except Exception:
        # Best effort: no crash.
        pass
