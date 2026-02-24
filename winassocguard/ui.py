# -*- coding: utf-8 -*-
"""
tkinter-based UI pieces.

Originally this project used small modal dialogs + a status table window.
This file now includes a compact "Control Panel" page:
- View protected extensions in one table
- Add / Remove
- Set baseline for selected extension(s)
- Switch language instantly
- Hide to tray / Exit
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple
import re

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk


StatusRow = Tuple[str, str, str]  # (ext, baseline_display, status_key)
LogRow = Tuple[str, str, str, str]  # (time, ext, event, detail)


@dataclass
class SettingsSnapshot:
    monitor_interval_sec: float
    notifications_enabled: bool
    auto_restore_enabled: bool
    auto_start_enabled: bool


def ask_extension(root: tk.Tk, title: str, prompt: str, initialvalue: str = "") -> Optional[str]:
    # simpledialog runs modal and returns a string or None.
    return simpledialog.askstring(title, prompt, parent=root, initialvalue=initialvalue)


def show_info(root: tk.Tk, title: str, message: str) -> None:
    messagebox.showinfo(title, message, parent=root)


def show_warning(root: tk.Tk, title: str, message: str) -> None:
    messagebox.showwarning(title, message, parent=root)


def show_error(root: tk.Tk, title: str, message: str) -> None:
    messagebox.showerror(title, message, parent=root)


def ask_yes_no(root: tk.Tk, title: str, message: str) -> bool:
    return messagebox.askyesno(title, message, parent=root)


# ---------------------------
# Legacy status table window
# ---------------------------

@dataclass
class StatusWindowTexts:
    title: str
    col_ext: str
    col_base: str
    col_curr: str
    btn_refresh: str
    btn_close: str


class StatusWindow:
    def __init__(
        self,
        root: tk.Tk,
        texts: StatusWindowTexts,
        get_rows: Callable[[], Sequence[StatusRow]],
    ):
        self.root = root
        self.texts = texts
        self.get_rows = get_rows
        self.top = tk.Toplevel(root)
        self.top.title(texts.title)
        self.top.geometry("860x420")
        self.top.minsize(760, 360)

        self._build()
        self.refresh()

    def _build(self) -> None:
        frm = ttk.Frame(self.top, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        columns = ("ext", "base", "curr")
        self.tree = ttk.Treeview(frm, columns=columns, show="headings")
        self.tree.heading("ext", text=self.texts.col_ext)
        self.tree.heading("base", text=self.texts.col_base)
        self.tree.heading("curr", text=self.texts.col_curr)

        self.tree.column("ext", width=120, anchor=tk.W, stretch=False)
        self.tree.column("base", width=360, anchor=tk.W, stretch=True)
        self.tree.column("curr", width=360, anchor=tk.W, stretch=True)

        vsb = ttk.Scrollbar(frm, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frm, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        frm.rowconfigure(0, weight=1)
        frm.columnconfigure(0, weight=1)

        btns = ttk.Frame(self.top, padding=(10, 0, 10, 10))
        btns.pack(fill=tk.X)

        self.btn_refresh = ttk.Button(btns, text=self.texts.btn_refresh, command=self.refresh)
        self.btn_refresh.pack(side=tk.LEFT)

        self.btn_close = ttk.Button(btns, text=self.texts.btn_close, command=self.top.destroy)
        self.btn_close.pack(side=tk.RIGHT)

    def refresh(self) -> None:
        # Clear
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        rows = list(self.get_rows())
        for ext, base, curr in rows:
            self.tree.insert("", tk.END, values=(ext, base, curr))


# ---------------------------
# New: Control Panel page
# ---------------------------

@dataclass
class ControlPanelCallbacks:
    # Translation function. Must accept (key, **kwargs).
    tr: Callable[..., str]
    get_rows: Callable[[], Sequence[StatusRow]]

    add_ext: Callable[[str], None]
    delete_exts: Callable[[Sequence[str]], None]
    import_common: Callable[[Sequence[str], bool], None]
    get_baseline_progid: Callable[[str], str]
    get_baseline_candidates: Callable[[str], Sequence[Tuple[str, str]]]
    set_baseline_manual: Callable[[str, str], None]
    get_logs: Callable[[str, int], Sequence[LogRow]]
    get_settings: Callable[[], SettingsSnapshot]
    update_settings: Callable[[SettingsSnapshot], None]
    delete_all: Callable[[], None]

    switch_language: Callable[[], None]
    hide_to_tray: Callable[[], None]
    exit_app: Callable[[], None]


class ControlPanel:
    """
    A single-window UX that centralizes all operations.
    """

    def __init__(self, root: tk.Tk, cb: ControlPanelCallbacks):
        self.root = root
        self.cb = cb

        self.status_var = tk.StringVar(value="")
        self.log_filter_var = tk.StringVar(value="")
        self.log_limit_var = tk.StringVar(value="200")
        self.log_count_var = tk.StringVar(value="")
        self.settings_interval_var = tk.StringVar(value="3")
        self.settings_notify_var = tk.BooleanVar(value=True)
        self.settings_auto_restore_var = tk.BooleanVar(value=True)
        self.settings_auto_start_var = tk.BooleanVar(value=False)

        self._build()
        self._load_settings()
        self.apply_texts()
        self.refresh()

    # ---- UI building ----
    def _build(self) -> None:
        self.root.geometry("1080x720")
        self.root.minsize(960, 620)

        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        # Header
        self.lbl_title = ttk.Label(outer, text="", font=("Segoe UI", 12, "bold"))
        self.lbl_title.pack(anchor=tk.W)

        self.lbl_sub = ttk.Label(outer, text="")
        self.lbl_sub.pack(anchor=tk.W, pady=(2, 10))

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_guard = ttk.Frame(self.notebook)
        self.tab_logs = ttk.Frame(self.notebook)
        self.tab_settings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_guard, text="")
        self.notebook.add(self.tab_logs, text="")
        self.notebook.add(self.tab_settings, text="")

        # Guard tab
        table_frm = ttk.Frame(self.tab_guard)
        table_frm.pack(fill=tk.BOTH, expand=True)

        cols = ("ext", "base")
        self.tree = ttk.Treeview(table_frm, columns=cols, show="headings", selectmode="extended")
        self.tree.heading("ext", text="")
        self.tree.heading("base", text="")

        self.tree.column("ext", width=120, anchor=tk.W, stretch=False)
        self.tree.column("base", width=460, anchor=tk.W, stretch=True)

        vsb = ttk.Scrollbar(table_frm, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frm, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frm.rowconfigure(0, weight=1)
        table_frm.columnconfigure(0, weight=1)

        # Buttons row (single line)
        btns = ttk.Frame(self.tab_guard)
        btns.pack(fill=tk.X, pady=(10, 2))

        self.btn_add = ttk.Button(btns, text="", command=self._on_add)
        self.btn_add.pack(side=tk.LEFT)

        self.btn_refresh = ttk.Button(btns, text="", command=self.refresh)
        self.btn_refresh.pack(side=tk.LEFT, padx=(8, 0))

        self.btn_import = ttk.Button(btns, text="", command=self._on_import_common)
        self.btn_import.pack(side=tk.LEFT, padx=(8, 0))

        self.btn_delete = ttk.Button(btns, text="", command=self._on_delete)
        self.btn_delete.pack(side=tk.LEFT, padx=(12, 0))

        self.btn_delete_all = ttk.Button(btns, text="", command=self._on_delete_all)
        self.btn_delete_all.pack(side=tk.LEFT, padx=(8, 0))

        self.btn_switch_lang = ttk.Button(btns, text="", command=self._on_switch_lang)
        self.btn_switch_lang.pack(side=tk.RIGHT, padx=(0, 8))

        self.btn_hide = ttk.Button(btns, text="", command=self._on_hide)
        self.btn_hide.pack(side=tk.RIGHT)

        self.btn_exit = ttk.Button(btns, text="", command=self._on_exit)
        self.btn_exit.pack(side=tk.RIGHT, padx=(0, 8))

        # Status bar
        status_frm = ttk.Frame(self.tab_guard)
        status_frm.pack(fill=tk.X)
        self.lbl_status = ttk.Label(status_frm, textvariable=self.status_var)
        self.lbl_status.pack(anchor=tk.W)

        # Logs tab
        logs_top = ttk.Frame(self.tab_logs)
        logs_top.pack(fill=tk.X, pady=(0, 8))
        self.lbl_log_filter = ttk.Label(logs_top, text="")
        self.lbl_log_filter.pack(side=tk.LEFT)
        self.ent_log_filter = ttk.Entry(logs_top, textvariable=self.log_filter_var, width=14)
        self.ent_log_filter.pack(side=tk.LEFT, padx=(6, 12))
        self.ent_log_filter.bind("<Return>", lambda _e: self.refresh_logs())

        self.lbl_log_limit = ttk.Label(logs_top, text="")
        self.lbl_log_limit.pack(side=tk.LEFT)
        self.cmb_log_limit = ttk.Combobox(
            logs_top,
            textvariable=self.log_limit_var,
            values=("50", "100", "200", "500"),
            width=6,
            state="readonly",
        )
        self.cmb_log_limit.pack(side=tk.LEFT, padx=(6, 12))
        self.cmb_log_limit.bind("<<ComboboxSelected>>", lambda _e: self.refresh_logs())
        self.btn_logs_refresh = ttk.Button(logs_top, text="", command=self.refresh_logs)
        self.btn_logs_refresh.pack(side=tk.LEFT)

        logs_table = ttk.Frame(self.tab_logs)
        logs_table.pack(fill=tk.BOTH, expand=True)

        log_cols = ("time", "ext", "event", "detail")
        self.tree_logs = ttk.Treeview(logs_table, columns=log_cols, show="headings")
        self.tree_logs.heading("time", text="")
        self.tree_logs.heading("ext", text="")
        self.tree_logs.heading("event", text="")
        self.tree_logs.heading("detail", text="")

        self.tree_logs.column("time", width=165, anchor=tk.W, stretch=False)
        self.tree_logs.column("ext", width=90, anchor=tk.W, stretch=False)
        self.tree_logs.column("event", width=160, anchor=tk.W, stretch=False)
        self.tree_logs.column("detail", width=520, anchor=tk.W, stretch=True)

        logs_vsb = ttk.Scrollbar(logs_table, orient="vertical", command=self.tree_logs.yview)
        logs_hsb = ttk.Scrollbar(logs_table, orient="horizontal", command=self.tree_logs.xview)
        self.tree_logs.configure(yscrollcommand=logs_vsb.set, xscrollcommand=logs_hsb.set)

        self.tree_logs.grid(row=0, column=0, sticky="nsew")
        logs_vsb.grid(row=0, column=1, sticky="ns")
        logs_hsb.grid(row=1, column=0, sticky="ew")

        logs_table.rowconfigure(0, weight=1)
        logs_table.columnconfigure(0, weight=1)

        self.lbl_log_count = ttk.Label(self.tab_logs, textvariable=self.log_count_var)
        self.lbl_log_count.pack(anchor=tk.W, pady=(6, 0))

        # Settings tab
        self.settings_box = ttk.LabelFrame(self.tab_settings, text="", padding=(12, 10))
        self.settings_box.pack(fill=tk.X, expand=False, pady=(2, 0))

        row0 = ttk.Frame(self.settings_box)
        row0.pack(fill=tk.X, pady=(0, 8))
        self.lbl_settings_interval = ttk.Label(row0, text="")
        self.lbl_settings_interval.pack(side=tk.LEFT)
        self.ent_settings_interval = ttk.Spinbox(
            row0,
            from_=1,
            to=60,
            increment=1,
            textvariable=self.settings_interval_var,
            width=8,
        )
        self.ent_settings_interval.pack(side=tk.LEFT, padx=(6, 8))
        self.lbl_settings_interval_unit = ttk.Label(row0, text="")
        self.lbl_settings_interval_unit.pack(side=tk.LEFT)

        self.chk_settings_notify = ttk.Checkbutton(
            self.settings_box, text="", variable=self.settings_notify_var
        )
        self.chk_settings_notify.pack(anchor=tk.W, pady=(4, 0))

        self.chk_settings_auto_restore = ttk.Checkbutton(
            self.settings_box, text="", variable=self.settings_auto_restore_var
        )
        self.chk_settings_auto_restore.pack(anchor=tk.W, pady=(4, 0))

        self.chk_settings_auto_start = ttk.Checkbutton(
            self.settings_box, text="", variable=self.settings_auto_start_var
        )
        self.chk_settings_auto_start.pack(anchor=tk.W, pady=(4, 0))

        footer_settings = ttk.Frame(self.tab_settings)
        footer_settings.pack(fill=tk.X, pady=(10, 0))
        self.btn_settings_apply = ttk.Button(
            footer_settings, text="", command=self._on_apply_settings
        )
        self.btn_settings_apply.pack(side=tk.LEFT)
        self.lbl_settings_hint = ttk.Label(footer_settings, text="")
        self.lbl_settings_hint.pack(side=tk.LEFT, padx=(12, 0))

    # ---- Text refresh (for language switching) ----
    def apply_texts(self) -> None:
        tr = self.cb.tr
        self.root.title(tr("panel_title"))
        self.lbl_title.configure(text=tr("panel_title"))
        self.lbl_sub.configure(text=tr("panel_subtitle"))
        self.notebook.tab(self.tab_guard, text=tr("tab_guard"))
        self.notebook.tab(self.tab_logs, text=tr("tab_logs"))
        self.notebook.tab(self.tab_settings, text=tr("tab_settings"))

        self.btn_add.configure(text=tr("btn_add"))
        self.btn_import.configure(text=tr("btn_import_common"))
        self.btn_delete.configure(text=tr("btn_delete"))
        self.btn_refresh.configure(text=tr("btn_refresh"))
        self.btn_delete_all.configure(text=tr("btn_delete_all"))
        self.btn_switch_lang.configure(text=tr("btn_switch_lang"))
        self.btn_hide.configure(text=tr("btn_hide"))
        self.btn_exit.configure(text=tr("btn_exit"))

        self.tree.heading("ext", text=tr("col_ext"))
        self.tree.heading("base", text=tr("col_base"))
        self.tree_logs.heading("time", text=tr("col_log_time"))
        self.tree_logs.heading("ext", text=tr("col_ext"))
        self.tree_logs.heading("event", text=tr("col_log_event"))
        self.tree_logs.heading("detail", text=tr("col_log_detail"))
        self.lbl_log_filter.configure(text=tr("lbl_log_filter"))
        self.lbl_log_limit.configure(text=tr("lbl_log_limit"))
        self.btn_logs_refresh.configure(text=tr("btn_refresh"))
        self.settings_box.configure(text=tr("grp_settings_guard"))
        self.lbl_settings_interval.configure(text=tr("lbl_settings_interval"))
        self.lbl_settings_interval_unit.configure(text=tr("lbl_settings_seconds"))
        self.chk_settings_notify.configure(text=tr("chk_settings_notifications"))
        self.chk_settings_auto_restore.configure(text=tr("chk_settings_guard_enabled"))
        self.chk_settings_auto_start.configure(text=tr("chk_settings_auto_start"))
        self.btn_settings_apply.configure(text=tr("btn_apply_settings"))
        self.lbl_settings_hint.configure(text=tr("msg_settings_hint"))

    # ---- helpers ----
    def _load_settings(self) -> None:
        settings = self.cb.get_settings()
        sec = float(settings.monitor_interval_sec)
        if abs(sec - round(sec)) < 1e-6:
            self.settings_interval_var.set(str(int(round(sec))))
        else:
            self.settings_interval_var.set(f"{sec:.1f}")
        self.settings_notify_var.set(bool(settings.notifications_enabled))
        self.settings_auto_restore_var.set(bool(settings.auto_restore_enabled))
        self.settings_auto_start_var.set(bool(settings.auto_start_enabled))

    def _selected_exts(self) -> List[str]:
        exts: List[str] = []
        for iid in self.tree.selection():
            vals = self.tree.item(iid, "values")
            if vals:
                exts.append(str(vals[0]))
        # unique while preserving order
        seen = set()
        out: List[str] = []
        for e in exts:
            if e not in seen:
                seen.add(e)
                out.append(e)
        return out

    def set_status(self, msg: str) -> None:
        self.status_var.set(msg)

    # ---- operations ----
    def refresh(self) -> None:
        tr = self.cb.tr

        # Clear
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        rows = list(self.cb.get_rows())

        for ext, base, _status in rows:
            self.tree.insert("", tk.END, values=(ext, base))

        self.set_status(f"{tr('col_ext')}: {len(rows)}")
        self.refresh_logs()

    def refresh_logs(self) -> None:
        tr = self.cb.tr
        try:
            limit = int((self.log_limit_var.get() or "200").strip())
        except Exception:
            limit = 200
            self.log_limit_var.set("200")

        ext_filter = (self.log_filter_var.get() or "").strip()
        rows = list(self.cb.get_logs(ext_filter, limit))

        for iid in self.tree_logs.get_children():
            self.tree_logs.delete(iid)

        for ts, ext, event, detail in rows:
            self.tree_logs.insert("", tk.END, values=(ts, ext, event, detail))

        self.log_count_var.set(tr("msg_log_count", n=len(rows)))

    def _on_apply_settings(self) -> None:
        tr = self.cb.tr
        try:
            sec = float((self.settings_interval_var.get() or "").strip())
        except Exception:
            show_warning(self.root, tr("dlg_info_title"), tr("msg_invalid_interval"))
            return
        settings = SettingsSnapshot(
            monitor_interval_sec=sec,
            notifications_enabled=bool(self.settings_notify_var.get()),
            auto_restore_enabled=bool(self.settings_auto_restore_var.get()),
            auto_start_enabled=bool(self.settings_auto_start_var.get()),
        )
        self.cb.update_settings(settings)
        self._load_settings()

    def _on_add(self) -> None:
        tr = self.cb.tr
        raw = ask_extension(self.root, tr("dlg_add_ext_title"), tr("dlg_add_ext_prompt"))
        if raw is None:
            return
        raw = raw.strip()
        if not raw:
            return
        self.cb.add_ext(raw)
        self.refresh()

    def _on_delete(self) -> None:
        tr = self.cb.tr
        exts = self._selected_exts()
        if not exts:
            show_warning(self.root, tr("dlg_info_title"), tr("msg_no_selection"))
            return
        msg = tr("msg_confirm_delete", n=len(exts), exts=", ".join(exts))
        if not ask_yes_no(self.root, tr("dlg_confirm_title"), msg):
            return
        self.cb.delete_exts(exts)
        self.refresh()
        self.set_status(tr("msg_deleted", n=len(exts)))

    def _on_delete_all(self) -> None:
        tr = self.cb.tr
        rows = list(self.cb.get_rows())
        n = len(rows)
        if n == 0:
            show_warning(self.root, tr("dlg_info_title"), tr("msg_delete_all_empty"))
            return
        if not ask_yes_no(self.root, tr("dlg_confirm_title"), tr("msg_confirm_delete_all", n=n)):
            return
        self.cb.delete_all()
        self.refresh()
        self.set_status(tr("msg_deleted_all", n=n))

    def _on_import_common(self) -> None:
        tr = self.cb.tr
        res = ask_import_common(self.root, tr)
        if res is None:
            return
        exts, capture_now = res
        if not exts:
            show_warning(self.root, tr("dlg_info_title"), tr("msg_import_common_none"))
            return
        self.cb.import_common(exts, capture_now)
        self.refresh()

    def _on_switch_lang(self) -> None:
        self.cb.switch_language()
        self.apply_texts()
        self.refresh()

    def _on_hide(self) -> None:
        self.cb.hide_to_tray()

    def _on_exit(self) -> None:
        self.cb.exit_app()

    def _on_tree_double_click(self, event) -> None:
        # Double-clicking the "baseline" column opens the app picker dialog.
        col = self.tree.identify_column(event.x)
        if col != "#2":
            return
        row = self.tree.identify_row(event.y)
        if not row:
            return
        vals = self.tree.item(row, "values")
        if not vals:
            return
        ext = str(vals[0]).strip()
        if not ext:
            return
        tr = self.cb.tr
        current_progid = self.cb.get_baseline_progid(ext)
        candidates = list(self.cb.get_baseline_candidates(ext))
        progid_raw = ask_baseline_progid(
            self.root,
            tr,
            ext=ext,
            current_progid=current_progid,
            candidates=candidates,
        )
        if progid_raw is None:
            return
        self.cb.set_baseline_manual(ext, progid_raw)
        self.refresh()


# ---------------------------
# Common extensions import dialog
# ---------------------------

# A curated list of common extensions. Kept small on purpose.
_COMMON_PRESETS = {
    "docs": [
        ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".txt", ".md",
    ],
    "images": [
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff",
    ],
    "code": [
        ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".cs", ".go", ".rs",
        ".php", ".html", ".css", ".json", ".xml", ".yaml", ".yml",
    ],
    "archives": [
        ".zip", ".7z", ".rar", ".tar", ".gz",
    ],
    "audio": [
        ".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg",
    ],
    "video": [
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm",
    ],
}


def ask_import_common(root: tk.Tk, tr: Callable[[str], str]) -> Optional[Tuple[List[str], bool]]:
    """Ask user to select common extensions to import.

    Returns (selected_exts, capture_now) or None if cancelled.
    """

    top = tk.Toplevel(root)
    top.title(tr("dlg_import_common_title"))
    top.geometry("860x640")
    top.minsize(760, 560)
    top.transient(root)

    # Result
    result: dict[str, object] = {"exts": None, "capture": True}
    manual_exts_var = tk.StringVar()

    def on_cancel() -> None:
        result["exts"] = None
        try:
            top.destroy()
        except Exception:
            pass

    def on_ok() -> None:
        exts: List[str] = []
        for ext, var in ext_vars.items():
            try:
                if bool(var.get()):
                    exts.append(ext)
            except Exception:
                continue
        manual_raw = (manual_exts_var.get() or "").strip()
        if manual_raw:
            for token in re.split(r"[\s,，;；]+", manual_raw):
                token = token.strip().lower()
                if not token:
                    continue
                if not token.startswith("."):
                    token = "." + token
                if token not in exts:
                    exts.append(token)
        result["exts"] = exts
        try:
            result["capture"] = bool(var_capture.get())
        except Exception:
            result["capture"] = True
        try:
            top.destroy()
        except Exception:
            pass

    top.protocol("WM_DELETE_WINDOW", on_cancel)

    outer = ttk.Frame(top, padding=12)
    outer.pack(fill=tk.BOTH, expand=True)

    lbl_desc = ttk.Label(outer, text=tr("dlg_import_common_desc"))
    lbl_desc.pack(anchor=tk.W)

    manual_frm = ttk.LabelFrame(outer, text=tr("dlg_import_common_manual"), padding=(10, 8))
    manual_frm.pack(fill=tk.X, pady=(10, 10))
    ttk.Label(manual_frm, text=tr("dlg_import_common_manual_hint")).pack(anchor=tk.W)
    ent_manual = ttk.Entry(manual_frm, textvariable=manual_exts_var)
    ent_manual.pack(fill=tk.X, pady=(6, 0))

    # Presets row
    presets_frm = ttk.LabelFrame(outer, text=tr("dlg_import_common_presets"), padding=(10, 8))
    presets_frm.pack(fill=tk.X, pady=(10, 10))

    # Prepare variables for every extension
    all_exts: List[str] = []
    for _k, lst in _COMMON_PRESETS.items():
        for e in lst:
            if e not in all_exts:
                all_exts.append(e)
    all_exts = sorted(all_exts)
    ext_vars: dict[str, tk.BooleanVar] = {e: tk.BooleanVar(value=False) for e in all_exts}

    def set_exts(ext_list: List[str], value: bool) -> None:
        for e in ext_list:
            if e in ext_vars:
                ext_vars[e].set(value)

    # Preset checkbuttons
    def add_preset_toggle(parent, key: str, exts: List[str], col: int) -> None:
        v = tk.BooleanVar(value=False)

        def on_toggle() -> None:
            set_exts(exts, bool(v.get()))

        chk = ttk.Checkbutton(parent, text=tr(key), variable=v, command=on_toggle)
        chk.grid(row=0, column=col, sticky="w", padx=(0, 12))

    add_preset_toggle(presets_frm, "preset_docs", _COMMON_PRESETS["docs"], 0)
    add_preset_toggle(presets_frm, "preset_images", _COMMON_PRESETS["images"], 1)
    add_preset_toggle(presets_frm, "preset_code", _COMMON_PRESETS["code"], 2)
    add_preset_toggle(presets_frm, "preset_archives", _COMMON_PRESETS["archives"], 3)
    add_preset_toggle(presets_frm, "preset_audio", _COMMON_PRESETS["audio"], 4)
    add_preset_toggle(presets_frm, "preset_video", _COMMON_PRESETS["video"], 5)

    # Select all / none
    btns_preset = ttk.Frame(presets_frm)
    btns_preset.grid(row=1, column=0, columnspan=6, sticky="w", pady=(10, 0))

    ttk.Button(btns_preset, text=tr("btn_select_all"), command=lambda: set_exts(all_exts, True)).pack(side=tk.LEFT)
    ttk.Button(btns_preset, text=tr("btn_select_none"), command=lambda: set_exts(all_exts, False)).pack(
        side=tk.LEFT, padx=(8, 0)
    )

    # Scrollable extension checklist
    list_frm = ttk.LabelFrame(outer, text=tr("dlg_import_common_list"), padding=(10, 8))
    list_frm.pack(fill=tk.BOTH, expand=True)

    canvas = tk.Canvas(list_frm, highlightthickness=0)
    vsb = ttk.Scrollbar(list_frm, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)

    inner = ttk.Frame(canvas)
    inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_inner_configure(_e=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_canvas_configure(e):
        # Make inner frame width track canvas
        try:
            canvas.itemconfigure(inner_id, width=e.width)
        except Exception:
            pass

    inner.bind("<Configure>", _on_inner_configure)
    canvas.bind("<Configure>", _on_canvas_configure)

    # Put checkboxes in a grid
    cols = 6
    for idx, ext in enumerate(all_exts):
        r = idx // cols
        c = idx % cols
        chk = ttk.Checkbutton(inner, text=ext, variable=ext_vars[ext])
        chk.grid(row=r, column=c, sticky="w", padx=(0, 12), pady=(2, 2))

    # Options
    opt_frm = ttk.Frame(outer)
    opt_frm.pack(fill=tk.X, pady=(10, 8))
    var_capture = tk.BooleanVar(value=True)
    ttk.Checkbutton(opt_frm, text=tr("chk_capture_after_import"), variable=var_capture).pack(side=tk.LEFT)

    # Footer buttons
    footer = ttk.Frame(outer)
    footer.pack(fill=tk.X)
    ttk.Button(footer, text=tr("btn_cancel"), command=on_cancel).pack(side=tk.RIGHT)
    ttk.Button(footer, text=tr("btn_confirm_import"), command=on_ok).pack(side=tk.RIGHT, padx=(0, 8))

    # Modal-ish behavior
    try:
        top.grab_set()
    except Exception:
        pass
    top.wait_window()

    exts_res = result.get("exts")
    if exts_res is None:
        return None
    return list(exts_res), bool(result.get("capture", True))


def ask_baseline_progid(
    root: tk.Tk,
    tr: Callable[[str], str],
    ext: str,
    current_progid: str,
    candidates: Sequence[Tuple[str, str]],
) -> Optional[str]:
    """
    Edit baseline with an app picker.
    Returns:
      - str: new baseline ProgId (empty string means clear)
      - None: cancelled
    """
    top = tk.Toplevel(root)
    top.title(tr("dlg_edit_baseline_title", ext=ext))
    top.geometry("780x560")
    top.minsize(720, 500)
    top.transient(root)

    result: dict[str, Optional[str]] = {"value": None}
    var_manual_input = tk.StringVar(value=(current_progid or "").strip())
    var_manual_enabled = tk.BooleanVar(value=False)

    def on_cancel() -> None:
        result["value"] = None
        try:
            top.destroy()
        except Exception:
            pass

    def on_clear() -> None:
        result["value"] = ""
        try:
            top.destroy()
        except Exception:
            pass

    def on_confirm() -> None:
        if bool(var_manual_enabled.get()):
            manual = (var_manual_input.get() or "").strip()
            if not manual:
                show_warning(top, tr("dlg_info_title"), tr("msg_manual_progid_required"))
                return
            result["value"] = manual
        else:
            sel = listbox.curselection()
            if not sel:
                show_warning(top, tr("dlg_info_title"), tr("msg_pick_app_required"))
                return
            idx = int(sel[0])
            if idx >= len(progid_by_index):
                show_warning(top, tr("dlg_info_title"), tr("msg_pick_app_required"))
                return
            result["value"] = progid_by_index[idx]
        try:
            top.destroy()
        except Exception:
            pass

    top.protocol("WM_DELETE_WINDOW", on_cancel)

    outer = ttk.Frame(top, padding=12)
    outer.pack(fill=tk.BOTH, expand=True)

    ttk.Label(outer, text=tr("dlg_edit_baseline_desc", ext=ext)).pack(anchor=tk.W)

    list_frm = ttk.LabelFrame(outer, text=tr("dlg_edit_baseline_candidates"), padding=(10, 8))
    list_frm.pack(fill=tk.BOTH, expand=True, pady=(10, 8))

    listbox = tk.Listbox(list_frm, activestyle="none")
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb = ttk.Scrollbar(list_frm, orient="vertical", command=listbox.yview)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.configure(yscrollcommand=vsb.set)

    progid_by_index: List[str] = []
    for progid, display in candidates:
        label = display or progid
        listbox.insert(tk.END, label)
        progid_by_index.append(progid)

    current_index = -1
    if current_progid:
        for idx, progid in enumerate(progid_by_index):
            if progid == current_progid:
                current_index = idx
                break

    if not progid_by_index:
        listbox.insert(tk.END, tr("dlg_edit_baseline_candidates_empty"))
    elif current_index >= 0:
        listbox.selection_set(current_index)
        listbox.see(current_index)

    listbox.bind("<Double-1>", lambda _e: on_confirm())

    adv_chk = ttk.Checkbutton(
        outer,
        text=tr("chk_show_manual_progid"),
        variable=var_manual_enabled,
    )
    adv_chk.pack(anchor=tk.W)

    manual_frm = ttk.LabelFrame(outer, text=tr("dlg_edit_baseline_manual"), padding=(10, 8))
    ent = ttk.Entry(manual_frm, textvariable=var_manual_input)
    ent.pack(fill=tk.X)

    def sync_manual_visibility() -> None:
        if bool(var_manual_enabled.get()):
            manual_frm.pack(fill=tk.X, pady=(8, 10))
            ent.focus_set()
            ent.select_range(0, tk.END)
        else:
            manual_frm.pack_forget()
            listbox.focus_set()

    adv_chk.configure(command=sync_manual_visibility)
    sync_manual_visibility()

    footer = ttk.Frame(outer)
    footer.pack(fill=tk.X)
    ttk.Button(footer, text=tr("btn_cancel"), command=on_cancel).pack(side=tk.RIGHT)
    ttk.Button(footer, text=tr("btn_confirm"), command=on_confirm).pack(side=tk.RIGHT, padx=(0, 8))
    ttk.Button(footer, text=tr("btn_clear_baseline"), command=on_clear).pack(side=tk.LEFT)

    try:
        top.grab_set()
    except Exception:
        pass
    top.wait_window()
    return result["value"]
