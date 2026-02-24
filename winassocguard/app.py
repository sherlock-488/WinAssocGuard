# -*- coding: utf-8 -*-
"""
Core application orchestration.

- Loads/saves config.json
- Runs a tray icon (pystray)
- Runs a monitoring thread (every 3s)
- Provides a single-window "Control Panel" (tkinter)
- Uses plyer for notifications
"""

from __future__ import annotations

import queue
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

import tkinter as tk
import winreg

from .config import AppConfig, ConfigManager
from .i18n import LANG_EN, LANG_ZH, t as i18n_t
from .icon import make_lock_icon
from .notify import notify
from .registry import (
    get_effective_progid,
    is_progid_valid,
    list_candidate_progids_for_ext,
    format_progid_for_picker,
    format_progid_for_display,
    is_valid_ext,
    normalize_ext,
    restore_to_baseline,
    list_user_fileexts,
)
from .tray import TrayActions, TrayController
from .ui import (
    ControlPanel,
    ControlPanelCallbacks,
    LogRow,
    SettingsSnapshot,
    StatusRow,
    ask_yes_no,
    show_error,
    show_info,
    show_warning,
)


def _clamp_lang(lang: str) -> str:
    lang = (lang or "").strip().lower()
    if lang.startswith("en"):
        return LANG_EN
    return LANG_ZH


def _format_exts_for_message(exts: List[str], max_items: int = 6) -> str:
    exts = [e for e in exts if e]
    if len(exts) <= max_items:
        return ", ".join(exts)
    head = ", ".join(exts[:max_items])
    return f"{head} ... (+{len(exts) - max_items})"


def _clamp_interval_seconds(value: float) -> float:
    try:
        out = float(value)
    except Exception:
        out = 3.0
    if out < 1.0:
        out = 1.0
    if out > 60.0:
        out = 60.0
    return out


@dataclass
class AppState:
    language: str = LANG_ZH
    protected_exts: Set[str] = field(default_factory=set)
    baseline_progid: Dict[str, str] = field(default_factory=dict)  # ext -> ProgId
    monitor_interval_sec: float = 3.0
    notifications_enabled: bool = True
    auto_restore_enabled: bool = True
    auto_start_enabled: bool = False
    lock: threading.RLock = field(default_factory=threading.RLock)

    def to_config(self) -> AppConfig:
        with self.lock:
            protected = sorted(self.protected_exts)
            base = {k: v for k, v in self.baseline_progid.items() if k in self.protected_exts and v}
            return AppConfig(
                language=self.language,
                protected_exts=protected,
                last_known_progid=base,
                monitor_interval_sec=_clamp_interval_seconds(self.monitor_interval_sec),
                notifications_enabled=bool(self.notifications_enabled),
                auto_restore_enabled=bool(self.auto_restore_enabled),
                auto_start_enabled=bool(self.auto_start_enabled),
            )

    @classmethod
    def from_config(cls, cfg: AppConfig) -> "AppState":
        language = _clamp_lang(cfg.language)
        protected: Set[str] = set()
        for ext in cfg.protected_exts or []:
            extn = normalize_ext(ext)
            if is_valid_ext(extn):
                protected.add(extn)
        baseline: Dict[str, str] = {}
        for k, v in (cfg.last_known_progid or {}).items():
            extn = normalize_ext(k)
            if extn in protected and isinstance(v, str) and v.strip():
                baseline[extn] = v.strip()
        return cls(
            language=language,
            protected_exts=protected,
            baseline_progid=baseline,
            monitor_interval_sec=_clamp_interval_seconds(cfg.monitor_interval_sec),
            notifications_enabled=bool(cfg.notifications_enabled),
            auto_restore_enabled=bool(cfg.auto_restore_enabled),
            auto_start_enabled=bool(cfg.auto_start_enabled),
        )


@dataclass
class EventLog:
    ts: float
    ext: str
    event_key: str
    detail: str = ""


class WinAssocGuardApp:
    STARTUP_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    STARTUP_VALUE_NAME = "WinAssocGuard"

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.config_path = base_dir / "config.json"
        self.cfg_mgr = ConfigManager(self.config_path)
        self.state = AppState.from_config(self.cfg_mgr.load())
        # Use real system startup state so UI reflects current machine setting.
        self.state.auto_start_enabled = self._read_startup_enabled()

        self.root: Optional[tk.Tk] = None
        self.panel: Optional[ControlPanel] = None
        self.gui_queue: "queue.Queue[Callable[[], None]]" = queue.Queue()

        self.stop_event = threading.Event()
        self.monitor_thread: Optional[threading.Thread] = None

        self.tray: Optional[TrayController] = None

        # For auto-restore spam control
        self._last_restore_ts: Dict[str, float] = {}
        self._event_logs: List[EventLog] = []
        self._max_log_entries: int = 1200

    def _build_startup_command(self) -> str:
        if getattr(sys, "frozen", False):
            return f'"{Path(sys.executable)}"'

        py = Path(sys.executable)
        if py.name.lower() == "python.exe":
            pyw = py.with_name("pythonw.exe")
            if pyw.exists():
                py = pyw
        script = self.base_dir / "main.py"
        return f'"{py}" "{script}"'

    def _read_startup_enabled(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.STARTUP_RUN_KEY, 0, winreg.KEY_READ) as k:
                val, _typ = winreg.QueryValueEx(k, self.STARTUP_VALUE_NAME)
                return isinstance(val, str) and bool(val.strip())
        except Exception:
            return False

    def _write_startup_enabled(self, enabled: bool) -> None:
        if enabled:
            cmd = self._build_startup_command()
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, self.STARTUP_RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, self.STARTUP_VALUE_NAME, 0, winreg.REG_SZ, cmd)
            return
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.STARTUP_RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, self.STARTUP_VALUE_NAME)
        except FileNotFoundError:
            pass
        except OSError:
            pass

    # --------- i18n helpers ---------
    def tr(self, key: str, **kwargs) -> str:
        with self.state.lock:
            lang = self.state.language
        return i18n_t(lang, key, **kwargs)

    def notify_i18n(self, msg_key: str, **kwargs) -> None:
        with self.state.lock:
            if not self.state.notifications_enabled:
                return
        title = self.tr("ntf_title")
        msg = self.tr(msg_key, **kwargs)
        notify(title=title, message=msg, timeout=5, app_name=title)

    def _append_log(self, event_key: str, ext: str = "", detail: str = "") -> None:
        extn = normalize_ext(ext) if ext else ""
        with self.state.lock:
            self._event_logs.append(EventLog(ts=time.time(), ext=extn, event_key=event_key, detail=detail))
            overflow = len(self._event_logs) - self._max_log_entries
            if overflow > 0:
                del self._event_logs[:overflow]

    # --------- queue / tkinter thread bridge ---------
    def enqueue_ui(self, func: Callable[[], None]) -> None:
        self.gui_queue.put(func)

    def _process_gui_queue(self) -> None:
        if self.root is None:
            return
        try:
            while True:
                task = self.gui_queue.get_nowait()
                try:
                    task()
                except Exception as e:
                    try:
                        show_error(self.root, self.tr("dlg_info_title"), self.tr("ntf_error", msg=str(e)))
                    except Exception:
                        pass
        except queue.Empty:
            pass
        self.root.after(120, self._process_gui_queue)

    # --------- state helpers ---------
    def _save_config(self) -> None:
        cfg = self.state.to_config()
        self.cfg_mgr.save(cfg)

    def get_status_rows(self) -> Sequence[StatusRow]:
        with self.state.lock:
            exts = sorted(self.state.protected_exts)
            baseline_map = dict(self.state.baseline_progid)

        rows: List[StatusRow] = []
        for ext in exts:
            base = baseline_map.get(ext, "")
            curr = get_effective_progid(ext) or ""
            if not base:
                status = "status_nobase"
            elif curr == base:
                status = "status_ok"
            else:
                status = "status_drift"
            rows.append((ext, format_progid_for_display(base), status))
        return rows

    def get_baseline_progid(self, ext: str) -> str:
        extn = normalize_ext(ext)
        if not extn:
            return ""
        with self.state.lock:
            return (self.state.baseline_progid.get(extn) or "").strip()

    def get_baseline_candidates(self, ext: str) -> Sequence[Tuple[str, str]]:
        extn = normalize_ext(ext)
        if not extn:
            return []

        with self.state.lock:
            baseline = (self.state.baseline_progid.get(extn) or "").strip()

        raw_candidates = list_candidate_progids_for_ext(extn)
        if baseline and baseline not in raw_candidates:
            raw_candidates.insert(0, baseline)

        out: List[Tuple[str, str]] = []
        for progid in raw_candidates:
            out.append((progid, format_progid_for_picker(progid)))
        return out

    def get_log_rows(self, ext_filter: str, limit: int) -> Sequence[LogRow]:
        raw = (ext_filter or "").strip()
        extn = normalize_ext(raw) if raw else ""
        try:
            max_rows = int(limit or 200)
        except Exception:
            max_rows = 200
        max_rows = max(10, min(max_rows, 1000))
        with self.state.lock:
            snapshot = list(self._event_logs)

        rows: List[LogRow] = []
        for entry in reversed(snapshot):
            if extn and entry.ext != extn:
                continue
            ts_local = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.ts))
            rows.append((ts_local, entry.ext or "-", self.tr(entry.event_key), entry.detail or ""))
            if len(rows) >= max_rows:
                break
        return rows

    def get_settings_snapshot(self) -> SettingsSnapshot:
        startup_enabled = self._read_startup_enabled()
        with self.state.lock:
            self.state.auto_start_enabled = startup_enabled
            return SettingsSnapshot(
                monitor_interval_sec=self.state.monitor_interval_sec,
                notifications_enabled=self.state.notifications_enabled,
                auto_restore_enabled=self.state.auto_restore_enabled,
                auto_start_enabled=startup_enabled,
            )

    def action_update_settings(self, settings: SettingsSnapshot) -> None:
        assert self.root is not None
        interval = _clamp_interval_seconds(settings.monitor_interval_sec)
        with self.state.lock:
            self.state.monitor_interval_sec = interval
            self.state.notifications_enabled = bool(settings.notifications_enabled)
            self.state.auto_restore_enabled = bool(settings.auto_restore_enabled)
        try:
            self._write_startup_enabled(bool(settings.auto_start_enabled))
        except Exception as e:
            show_warning(self.root, self.tr("dlg_info_title"), self.tr("msg_startup_toggle_failed", msg=str(e)))
        with self.state.lock:
            self.state.auto_start_enabled = self._read_startup_enabled()
        self._save_config()
        self._append_log(
            "log_event_settings_updated",
            detail=self.tr(
                "msg_settings_changed_detail",
                sec=interval,
                notify="on" if settings.notifications_enabled else "off",
                auto="on" if settings.auto_restore_enabled else "off",
                start="on" if settings.auto_start_enabled else "off",
            ),
        )
        show_info(self.root, self.tr("dlg_info_title"), self.tr("msg_settings_saved", sec=interval))

    # --------- actions for control panel ---------
    def action_add_extension_value(self, ext_raw: str) -> None:
        assert self.root is not None
        extn = normalize_ext(ext_raw)
        if not is_valid_ext(extn):
            show_warning(self.root, self.tr("dlg_info_title"), self.tr("dlg_invalid_ext"))
            return

        with self.state.lock:
            already = extn in self.state.protected_exts
            self.state.protected_exts.add(extn)

        self._save_config()
        if not already:
            show_info(self.root, self.tr("dlg_info_title"), self.tr("dlg_added_hint", ext=extn))
            self.notify_i18n("ntf_added", ext=extn)
            self._append_log("log_event_ext_added", ext=extn)

    def action_delete_extensions(self, exts: Sequence[str]) -> None:
        deleted: List[str] = []
        with self.state.lock:
            for ext in exts:
                extn = normalize_ext(ext)
                self.state.protected_exts.discard(extn)
                if extn in self.state.baseline_progid:
                    self.state.baseline_progid.pop(extn, None)
                if extn:
                    deleted.append(extn)
        self._save_config()
        for extn in deleted:
            self._append_log("log_event_ext_deleted", ext=extn)

    def action_delete_all(self) -> None:
        with self.state.lock:
            n = len(self.state.protected_exts)
            self.state.protected_exts.clear()
            self.state.baseline_progid.clear()
        self._save_config()
        if n > 0:
            self._append_log("log_event_deleted_all", detail=self.tr("msg_deleted_all", n=n))

    def action_import_common(self, exts: Sequence[str], capture_now: bool = True) -> None:
        """Import a list of (common) extensions into the protected list.

        Optionally capture current ProgId as baseline right away.
        """
        assert self.root is not None

        # Normalize + validate + unique (preserve order)
        invalid = 0
        seen: Set[str] = set()
        cleaned: List[str] = []
        for ext in exts:
            extn = normalize_ext(ext)
            if not is_valid_ext(extn):
                invalid += 1
                continue
            if extn in seen:
                continue
            seen.add(extn)
            cleaned.append(extn)

        if not cleaned:
            show_warning(self.root, self.tr("dlg_info_title"), self.tr("msg_import_common_none"))
            return

        with self.state.lock:
            before_cnt = len(self.state.protected_exts)
            for extn in cleaned:
                self.state.protected_exts.add(extn)
            after_cnt = len(self.state.protected_exts)

        added = max(0, after_cnt - before_cnt)
        captured = 0
        if capture_now:
            for extn in cleaned:
                progid = get_effective_progid(extn)
                if progid and is_progid_valid(progid):
                    with self.state.lock:
                        self.state.baseline_progid[extn] = progid
                    captured += 1

        self._save_config()
        for extn in cleaned:
            self._append_log("log_event_imported_ext", ext=extn)
        show_info(
            self.root,
            self.tr("dlg_info_title"),
            self.tr(
                "msg_import_common_done",
                selected=len(cleaned),
                added=added,
                captured=captured,
                invalid=invalid,
            ),
        )
        self.notify_i18n("ntf_import_common_done", n=len(cleaned))

    def action_capture_selected(self, exts: Sequence[str]) -> None:
        assert self.root is not None
        captured = 0
        for ext in exts:
            extn = normalize_ext(ext)
            progid = get_effective_progid(extn)
            if progid and is_progid_valid(progid):
                with self.state.lock:
                    self.state.baseline_progid[extn] = progid
                captured += 1

        self._save_config()
        if captured > 0:
            show_info(self.root, self.tr("dlg_info_title"), self.tr("msg_capture_sel_done", n=captured))
            self.notify_i18n("ntf_capture_ok", n=captured)
            self._append_log("log_event_capture_selected", detail=self.tr("msg_capture_sel_done", n=captured))
        else:
            show_warning(self.root, self.tr("dlg_info_title"), self.tr("msg_capture_sel_none"))

    def action_capture_all(self) -> None:
        # Capture baselines for all protected exts.
        assert self.root is not None
        captured = 0
        with self.state.lock:
            exts = sorted(self.state.protected_exts)

        for ext in exts:
            progid = get_effective_progid(ext)
            if progid and is_progid_valid(progid):
                with self.state.lock:
                    self.state.baseline_progid[ext] = progid
                captured += 1

        self._save_config()
        if captured > 0:
            show_info(self.root, self.tr("dlg_info_title"), self.tr("dlg_capture_done", n=captured))
            self.notify_i18n("ntf_capture_ok", n=captured)
            self._append_log("log_event_capture_all", detail=self.tr("dlg_capture_done", n=captured))
        else:
            show_warning(self.root, self.tr("dlg_info_title"), self.tr("dlg_capture_none"))

    
    def action_import_defaults_and_capture(self) -> None:
        """
        One-click setup:
        - Enumerate extensions that already have a per-user default (UserChoice)
        - Add them to protected list
        - Capture current ProgId as baseline immediately

        This avoids the "add from scratch" friction.
        """
        assert self.root is not None

        exts = list_user_fileexts(only_userchoice=True)
        found = len(exts)
        if found == 0:
            show_warning(self.root, self.tr("dlg_info_title"), self.tr("msg_import_none"))
            return

        # Resolve current ProgId and keep only valid ones
        pairs: List[Tuple[str, str]] = []
        skipped = 0
        for ext in exts:
            progid = get_effective_progid(ext)
            if progid and is_progid_valid(progid):
                pairs.append((ext, progid))
            else:
                skipped += 1

        if not pairs:
            show_warning(self.root, self.tr("dlg_info_title"), self.tr("msg_import_none_valid", found=found))
            return

        # If there are many, confirm (so we don't accidentally guard 200+ extensions)
        if len(pairs) >= 30:
            if not ask_yes_no(
                self.root,
                self.tr("dlg_confirm_title"),
                self.tr("msg_import_confirm", n=len(pairs)),
            ):
                return

        with self.state.lock:
            before_cnt = len(self.state.protected_exts)
            for ext, progid in pairs:
                self.state.protected_exts.add(ext)
                self.state.baseline_progid[ext] = progid
            after_cnt = len(self.state.protected_exts)

        added = max(0, after_cnt - before_cnt)
        captured = len(pairs)

        self._save_config()
        show_info(
            self.root,
            self.tr("dlg_info_title"),
            self.tr("msg_import_done", found=found, imported=captured, added=added, skipped=skipped),
        )
        self.notify_i18n("ntf_import_done", n=captured)
        self._append_log("log_event_import_defaults", detail=self.tr("msg_import_done", found=found, imported=captured, added=added, skipped=skipped))

    def action_restore_selected(self, exts: Sequence[str]) -> None:
        assert self.root is not None
        processed = 0
        ok_cnt = 0

        with self.state.lock:
            baseline_map = dict(self.state.baseline_progid)

        for ext in exts:
            extn = normalize_ext(ext)
            baseline = baseline_map.get(extn, "")
            if not baseline:
                continue
            processed += 1
            res = restore_to_baseline(extn, baseline)
            if res.ok:
                ok_cnt += 1
                self._append_log("log_event_restore_ok", ext=extn)
            else:
                self._append_log("log_event_restore_failed", ext=extn, detail=res.error or "")

        self._save_config()
        show_info(self.root, self.tr("dlg_info_title"), self.tr("msg_restore_sel_done", n=processed, ok=ok_cnt))
        self.notify_i18n("ntf_force_restore_ok", n=ok_cnt)

    def action_restore_all(self) -> None:
        # Restore all baselines.
        assert self.root is not None
        with self.state.lock:
            items = sorted((ext, progid) for ext, progid in self.state.baseline_progid.items() if progid)

        processed = 0
        ok_cnt = 0
        for ext, progid in items:
            processed += 1
            res = restore_to_baseline(ext, progid)
            if res.ok:
                ok_cnt += 1
                self._append_log("log_event_restore_ok", ext=ext)
            else:
                self._append_log("log_event_restore_failed", ext=ext, detail=res.error or "")

        self._save_config()
        show_info(self.root, self.tr("dlg_info_title"), self.tr("dlg_force_restore_done", n=processed))
        self.notify_i18n("ntf_force_restore_ok", n=ok_cnt)

    def action_set_baseline_manual(self, ext: str, progid_raw: str) -> None:
        """
        Set baseline for a single ext. Empty progid_raw => clear baseline.
        """
        assert self.root is not None
        extn = normalize_ext(ext)
        progid = (progid_raw or "").strip()

        if not extn:
            return

        if not progid:
            with self.state.lock:
                self.state.baseline_progid.pop(extn, None)
            self._save_config()
            show_info(self.root, self.tr("dlg_info_title"), self.tr("msg_baseline_cleared", ext=extn))
            self._append_log("log_event_baseline_cleared", ext=extn)
            return

        if not is_progid_valid(progid):
            show_warning(self.root, self.tr("dlg_info_title"), self.tr("msg_invalid_progid", progid=progid))
            return

        with self.state.lock:
            self.state.baseline_progid[extn] = progid
        self._save_config()
        show_info(self.root, self.tr("dlg_info_title"), self.tr("msg_baseline_set", ext=extn))
        self._append_log("log_event_baseline_set", ext=extn, detail=format_progid_for_display(progid))

    def action_switch_language(self) -> None:
        with self.state.lock:
            self.state.language = LANG_EN if self.state.language == LANG_ZH else LANG_ZH
        self._save_config()
        # Update tray immediately
        if self.tray is not None:
            self.tray.update_menu()
        # Update window texts
        if self.root is not None:
            try:
                self.root.title(self.tr("panel_title"))
            except Exception:
                pass
        if self.panel is not None:
            try:
                self.panel.apply_texts()
            except Exception:
                pass

    def action_hide_to_tray(self) -> None:
        if self.root is None:
            return
        try:
            self.root.withdraw()
        except Exception:
            return
        self.notify_i18n("ntf_hidden")

    def action_show_panel(self) -> None:
        if self.root is None:
            return
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass
        if self.panel is not None:
            try:
                self.panel.refresh()
            except Exception:
                pass

    def action_exit(self) -> None:
        # Called on tkinter thread.
        self.stop_event.set()
        self._save_config()
        if self.tray is not None:
            self.tray.stop()
        if self.root is not None:
            try:
                self.root.quit()
            except Exception:
                pass

    # --------- monitoring thread ---------
    def _monitor_loop(self) -> None:
        cooldown = 12.0  # seconds per extension to avoid toast spam on stubborn systems

        while not self.stop_event.is_set():
            to_restore: List[Tuple[str, str, str]] = []

            with self.state.lock:
                baselines = dict(self.state.baseline_progid)
                interval = _clamp_interval_seconds(self.state.monitor_interval_sec)
                auto_restore_enabled = bool(self.state.auto_restore_enabled)

            if not auto_restore_enabled:
                for _ in range(int(interval * 10)):
                    if self.stop_event.is_set():
                        break
                    time.sleep(0.1)
                continue

            now_ts = time.time()
            for ext, baseline in baselines.items():
                if not baseline:
                    continue

                last = self._last_restore_ts.get(ext, 0.0)
                if now_ts - last < cooldown:
                    continue

                current = get_effective_progid(ext)
                if current != baseline:
                    to_restore.append((ext, baseline, current or ""))

            ok_exts: List[str] = []
            fail_exts: List[str] = []

            for ext, baseline, prev in to_restore:
                self._last_restore_ts[ext] = time.time()
                res = restore_to_baseline(ext, baseline)
                if res.ok:
                    ok_exts.append(ext)
                    self._append_log(
                        "log_event_auto_restore_ok",
                        ext=ext,
                        detail=self.tr("msg_log_restore_detail", prev=prev or "-", base=baseline),
                    )
                else:
                    fail_exts.append(ext)
                    self._append_log("log_event_auto_restore_failed", ext=ext, detail=res.error or "")

            if ok_exts:
                self.notify_i18n("ntf_auto_restore_ok", exts=_format_exts_for_message(ok_exts))
            if fail_exts:
                self.notify_i18n("ntf_auto_restore_fail", exts=_format_exts_for_message(fail_exts))

            for _ in range(int(interval * 10)):
                if self.stop_event.is_set():
                    break
                time.sleep(0.1)

    # --------- lifecycle ---------
    def run(self) -> None:
        # Create Tk root on main thread (visible control panel)
        self.root = tk.Tk()
        self.root.title(self.tr("panel_title"))
        self.root.after(120, self._process_gui_queue)

        # Close button hides to tray (common tray-app behavior)
        self.root.protocol("WM_DELETE_WINDOW", self.action_hide_to_tray)

        # Build control panel
        callbacks = ControlPanelCallbacks(
            tr=lambda key, **kwargs: self.tr(key, **kwargs),
            get_rows=self.get_status_rows,
            add_ext=self.action_add_extension_value,
            delete_exts=self.action_delete_extensions,
            import_common=self.action_import_common,
            get_baseline_progid=self.get_baseline_progid,
            get_baseline_candidates=self.get_baseline_candidates,
            set_baseline_manual=self.action_set_baseline_manual,
            get_logs=self.get_log_rows,
            get_settings=self.get_settings_snapshot,
            update_settings=self.action_update_settings,
            delete_all=self.action_delete_all,
            switch_language=self.action_switch_language,
            hide_to_tray=self.action_hide_to_tray,
            exit_app=self.action_exit,
        )
        self.panel = ControlPanel(self.root, cb=callbacks)

        # Tray
        image = make_lock_icon(64)

        actions = TrayActions(
            open_panel=lambda: self.enqueue_ui(self.action_show_panel),
            switch_language=lambda: self.enqueue_ui(self.action_switch_language),
        )

        self.tray = TrayController(
            image=image,
            get_lang=lambda: self.state.language,
            tr=lambda key: self.tr(key),
            actions=actions,
        )

        # Start monitor
        self.monitor_thread = threading.Thread(target=self._monitor_loop, name="WinAssocGuardMonitor", daemon=True)
        self.monitor_thread.start()

        # Start tray
        self.tray.run_detached()

        # Run tkinter loop (keeps the process alive)
        self.root.mainloop()

        # Cleanup (best effort)
        self.stop_event.set()
        try:
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=1.5)
        except Exception:
            pass
        self._save_config()
