# -*- coding: utf-8 -*-
"""
System tray integration via pystray.

The tray menu is built dynamically from i18n keys so language switching is instant.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pystray
from pystray import Menu as TrayMenu
from pystray import MenuItem as TrayMenuItem


@dataclass
class TrayActions:
    open_panel: Callable[[], None]
    switch_language: Callable[[], None]


class TrayController:
    def __init__(
        self,
        image,
        get_lang: Callable[[], str],
        tr: Callable[[str], str],
        actions: TrayActions,
    ):
        """
        tr: callable that maps i18n keys -> localized strings
        """
        self.image = image
        self.get_lang = get_lang
        self.tr = tr
        self.actions = actions
        self.icon = pystray.Icon(self.tr("app_name"), self.image, self.tr("app_name"), self._build_menu())

    def _build_menu(self) -> TrayMenu:
        # Labels are callables so they re-evaluate when language changes.
        def label(key: str):
            return lambda item: self.tr(key)

        return TrayMenu(
            TrayMenuItem(label("menu_open_panel"), lambda _icon, _item: self.actions.open_panel()),
            TrayMenuItem(label("menu_switch_lang"), lambda _icon, _item: self.actions.switch_language()),
        )

    def update_menu(self) -> None:
        self.icon.menu = self._build_menu()
        try:
            self.icon.update_menu()
        except Exception:
            # On some backends, update_menu is not available or not needed.
            pass

    def run_detached(self) -> None:
        self.icon.run_detached()

    def stop(self) -> None:
        try:
            self.icon.stop()
        except Exception:
            pass
