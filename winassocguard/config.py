# -*- coding: utf-8 -*-
"""
Config persistence in a human-readable JSON file.

Spec fields:
- protected_exts: list[str]
- last_known_progid: dict[str, str]   (baseline map)
- language: "zh" | "en"
- monitor_interval_sec: float
- notifications_enabled: bool
- auto_restore_enabled: bool
- auto_start_enabled: bool
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


DEFAULT_CONFIG_FILENAME = "config.json"


def _to_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in ("1", "true", "yes", "on"):
            return True
        if s in ("0", "false", "no", "off"):
            return False
    return default


@dataclass
class AppConfig:
    language: str = "zh"
    protected_exts: List[str] = field(default_factory=list)
    last_known_progid: Dict[str, str] = field(default_factory=dict)
    monitor_interval_sec: float = 3.0
    notifications_enabled: bool = True
    auto_restore_enabled: bool = True
    auto_start_enabled: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        language = data.get("language", "zh")
        protected_exts = data.get("protected_exts", []) or []
        last_known_progid = data.get("last_known_progid", {}) or {}
        monitor_interval_sec = data.get("monitor_interval_sec", 3.0)
        notifications_enabled = data.get("notifications_enabled", True)
        auto_restore_enabled = data.get("auto_restore_enabled", True)
        auto_start_enabled = data.get("auto_start_enabled", False)
        # Normalize types
        if not isinstance(protected_exts, list):
            protected_exts = []
        if not isinstance(last_known_progid, dict):
            last_known_progid = {}
        try:
            monitor_interval_sec = float(monitor_interval_sec)
        except Exception:
            monitor_interval_sec = 3.0
        if monitor_interval_sec < 1.0:
            monitor_interval_sec = 1.0
        if monitor_interval_sec > 60.0:
            monitor_interval_sec = 60.0
        notifications_enabled = _to_bool(notifications_enabled, True)
        auto_restore_enabled = _to_bool(auto_restore_enabled, True)
        auto_start_enabled = _to_bool(auto_start_enabled, False)
        return cls(
            language=str(language),
            protected_exts=[str(x) for x in protected_exts],
            last_known_progid={str(k): str(v) for k, v in last_known_progid.items()},
            monitor_interval_sec=monitor_interval_sec,
            notifications_enabled=notifications_enabled,
            auto_restore_enabled=auto_restore_enabled,
            auto_start_enabled=auto_start_enabled,
        )

    def to_dict(self) -> dict:
        return {
            "language": self.language,
            "protected_exts": self.protected_exts,
            "last_known_progid": self.last_known_progid,
            "monitor_interval_sec": self.monitor_interval_sec,
            "notifications_enabled": self.notifications_enabled,
            "auto_restore_enabled": self.auto_restore_enabled,
            "auto_start_enabled": self.auto_start_enabled,
        }


class ConfigManager:
    def __init__(self, config_path: Path):
        self.config_path = config_path

    def load(self) -> AppConfig:
        if not self.config_path.exists():
            return AppConfig()
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return AppConfig()
            return AppConfig.from_dict(data)
        except Exception:
            # If config is corrupted, start fresh but do not crash.
            return AppConfig()

    def save(self, config: AppConfig) -> None:
        try:
            payload = json.dumps(config.to_dict(), ensure_ascii=False, indent=2)
            self.config_path.write_text(payload, encoding="utf-8")
        except Exception:
            # Don't crash on disk issues; user can still use the app.
            pass
