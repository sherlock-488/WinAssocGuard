# -*- coding: utf-8 -*-
"""
Simple i18n (internationalization) helper.

We keep it intentionally tiny: a single translation dict + a `t()` function.
"""

from __future__ import annotations

from typing import Any, Dict


LANG_ZH = "zh"
LANG_EN = "en"

_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    LANG_ZH: {
        # App / tray
        "app_name": "WinAssocGuard",
        "menu_open_panel": "打开管理面板",
        "menu_add_ext": "添加守护扩展名…",
        "menu_capture": "捕获当前关联为基准",
        "menu_status": "查看当前守护状态",
        "menu_force_restore": "强制全部恢复",
        "menu_switch_lang": "切换到英文 / Switch to English",
        "menu_exit": "退出",

        # Control Panel
        "panel_title": "WinAssocGuard 管理面板",
        "panel_subtitle": "守护扩展名（检测到关联被抢占会自动恢复）",
        "tab_guard": "守护列表",
        "tab_logs": "日志",
        "tab_settings": "设置",
        "panel_ext_label": "扩展名：",
        "panel_ext_placeholder": "例如 .pdf",
        "btn_add": "添加",
        "btn_delete": "删除",
        "btn_delete_all": "删除全部",
        "btn_refresh": "刷新",
        "btn_import_defaults": "导入当前默认并捕获",
        "btn_import_common": "导入后缀",
        "btn_capture_selected": "选中设为基准",
        "btn_set_baseline": "设为基准",
        "btn_capture_all": "一键设为当前基准",
        "btn_restore_selected": "恢复选中",
        "btn_restore_all": "恢复全部",
        "btn_edit_baseline": "修改基准…",
        "btn_switch_lang": "中文/English",
        "btn_hide": "隐藏到托盘",
        "btn_exit": "退出程序",

        # Table columns
        "col_ext": "扩展名",
        "col_base": "当前基准（应用）",
        "col_curr": "当前实际（ProgId）",
        "col_status": "状态",
        "col_log_time": "时间",
        "col_log_event": "事件",
        "col_log_detail": "详情",

        # Status strings
        "status_ok": "一致",
        "status_drift": "已偏离",
        "status_nobase": "未捕获",

        # Dialogs / common UI
        "dlg_add_ext_title": "添加守护扩展名",
        "dlg_add_ext_prompt": "请输入扩展名（例如：.py / .docx / .pdf）：",
        "dlg_invalid_ext": "扩展名格式不正确。示例：.pdf",
        "dlg_info_title": "提示",
        "dlg_confirm_title": "确认",
        "dlg_added_hint": "已添加 {ext}\n\n下一步：请手动把该扩展名设置为你想要的默认程序，然后点击“一键设为当前基准”（或选中后点“选中设为基准”）。",
        "dlg_capture_done": "已捕获 {n} 个扩展名的关联为基准。",
        "dlg_capture_none": "没有捕获到任何有效 ProgId。\n\n请先手动设置默认程序，然后再捕获。",
        "dlg_force_restore_done": "强制恢复完成：已处理 {n} 个扩展名。",
        "dlg_status_title": "当前守护状态",
        "dlg_status_col_ext": "扩展名",
        "dlg_status_col_base": "保存的基准程序（ProgId）",
        "dlg_status_col_curr": "当前实际程序（ProgId）",
        "dlg_refresh": "刷新",
        "dlg_close": "关闭",

        # Panel messages
        "msg_no_selection": "请先选中一行。",
        "msg_import_none": "没有找到任何已设置过默认应用的扩展名（UserChoice）。\n\n你可以手动添加扩展名，然后点“一键设为当前基准”。",
        "msg_import_none_valid": "找到了 {found} 个扩展名，但没有任何有效 ProgId 可以捕获（可能相关软件已卸载）。",
        "msg_import_confirm": "检测到 {n} 个扩展名已有用户默认设置（UserChoice）。\n\n导入并立刻捕获为基准吗？\n（建议只守护 5~20 个，导入后可在表格里删除不需要的。）",
        "msg_import_done": "导入完成：发现 {found} 个，成功导入 {imported} 个（新增 {added} 个），跳过 {skipped} 个无效项。",
        "msg_select_one": "请只选中一行。",
        "msg_deleted": "已删除 {n} 项。",
        "msg_capture_sel_done": "已为选中项捕获基准：{n} 项。",
        "msg_capture_sel_none": "选中项没有捕获到任何有效 ProgId。\n\n请先在系统里手动设置默认程序。",
        "msg_restore_sel_done": "恢复完成：已处理 {n} 项，成功 {ok} 项。",
        "msg_confirm_delete": "确定要删除选中的 {n} 项吗？\n\n{exts}",
        "msg_confirm_delete_all": "确定要删除全部 {n} 项吗？\n\n这将清空守护列表和所有已保存的基准。",
        "msg_delete_all_empty": "当前没有任何守护项。",
        "msg_deleted_all": "已删除全部 {n} 项。",
        "msg_log_count": "共 {n} 条",
        "msg_invalid_interval": "检测间隔必须是 1 到 60 秒之间的数字。",
        "msg_settings_saved": "设置已保存（检测间隔 {sec} 秒）。",
        "msg_settings_hint": "提示：修改后会立即生效。",
        "msg_settings_changed_detail": "间隔={sec}s, 通知={notify}, 守护={auto}, 开机启动={start}",
        "msg_startup_toggle_failed": "设置开机启动失败：{msg}",
        "msg_log_restore_detail": "从 {prev} 恢复到 {base}",

        "msg_import_common_none": "请至少选择一个后缀。",
        "msg_import_common_done": "导入完成：选择 {selected} 个，新增 {added} 个，捕获 {captured} 个基准，跳过 {invalid} 个无效项。",
        "msg_edit_baseline_prompt": "为 {ext} 输入新的基准 ProgId（留空表示清除基准）：",
        "msg_invalid_progid": "ProgId 无效或不存在：{progid}",
        "msg_baseline_cleared": "已清除 {ext} 的基准。",
        "msg_baseline_set": "已更新 {ext} 的基准。",
        "msg_hidden_to_tray": "已隐藏到托盘，仍在后台守护。",
        "msg_open_baseline_no_base": "{ext} 还没有基准。",
        "msg_open_baseline_no_target": "无法定位该基准对应的可执行程序：{progid}",
        "msg_open_baseline_failed": "打开失败：{target}\n{msg}",
        "msg_pick_app_required": "请先在列表中选择一个应用。",
        "msg_manual_progid_required": "请先输入 ProgId，或关闭手动模式后直接选择应用。",

        # Import common dialog
        "dlg_import_common_title": "导入常见后缀",
        "dlg_import_common_desc": "选择要守护的常见后缀。也可以先导入，再在表格里删除不需要的项。",
        "dlg_import_common_manual": "手动输入",
        "dlg_import_common_manual_hint": "输入后缀（如 .mov .mkv），用逗号、分号或空格分隔。",
        "dlg_import_common_presets": "快速选择",
        "dlg_import_common_list": "常见后缀列表",
        "preset_docs": "文档",
        "preset_images": "图片",
        "preset_code": "代码",
        "preset_archives": "压缩包",
        "preset_audio": "音频",
        "preset_video": "视频",
        "btn_select_all": "全选",
        "btn_select_none": "全不选",
        "chk_capture_after_import": "导入后立即捕获当前关联为基准",
        "btn_import": "导入",
        "btn_confirm_import": "确认导入",
        "btn_cancel": "取消",

        # Notifications
        "ntf_title": "WinAssocGuard",
        "ntf_auto_restore_ok": "自动恢复成功：{exts}",
        "ntf_auto_restore_fail": "自动恢复失败：{exts}",
        "ntf_capture_ok": "捕获成功：{n} 项",
        "ntf_import_done": "已导入并捕获：{n} 项",
        "ntf_import_common_done": "已导入常见后缀：{n} 项",
        "ntf_force_restore_ok": "强制恢复完成：{n} 项",
        "ntf_added": "已添加守护扩展：{ext}",
        "ntf_hidden": "已隐藏到托盘，仍在后台守护。",
        "ntf_error": "发生错误：{msg}",

        "lbl_log_filter": "按后缀过滤：",
        "lbl_log_limit": "最近：",
        "grp_settings_guard": "守护设置",
        "lbl_settings_interval": "检测间隔",
        "lbl_settings_seconds": "秒",
        "chk_settings_notifications": "启用系统通知",
        "chk_settings_guard_enabled": "开启守护（自动恢复）",
        "chk_settings_auto_start": "开机自启动",
        "btn_apply_settings": "应用设置",

        "btn_confirm": "确认",
        "btn_clear_baseline": "清除基准",
        "dlg_edit_baseline_title": "修改基准：{ext}",
        "dlg_edit_baseline_desc": "为后缀 {ext} 选择一个应用作为基准。",
        "dlg_edit_baseline_candidates": "可选应用",
        "dlg_edit_baseline_candidates_empty": "暂无可选应用，请开启手动模式输入 ProgId",
        "dlg_edit_baseline_manual": "手动输入 ProgId（高级）",
        "chk_show_manual_progid": "手动输入 ProgId（高级）",

        "log_event_ext_added": "添加守护后缀",
        "log_event_ext_deleted": "删除守护后缀",
        "log_event_deleted_all": "删除全部守护",
        "log_event_imported_ext": "导入后缀",
        "log_event_capture_selected": "捕获选中基准",
        "log_event_capture_all": "捕获全部基准",
        "log_event_import_defaults": "导入当前默认",
        "log_event_restore_ok": "手动恢复成功",
        "log_event_restore_failed": "手动恢复失败",
        "log_event_baseline_set": "修改基准",
        "log_event_baseline_cleared": "清除基准",
        "log_event_auto_restore_ok": "自动恢复成功",
        "log_event_auto_restore_failed": "自动恢复失败",
        "log_event_settings_updated": "更新设置",

        # Errors / Warnings
        "warn_windows_only": "本程序仅支持 Windows。",
    },
    LANG_EN: {
        # App / tray
        "app_name": "WinAssocGuard",
        "menu_open_panel": "Open Control Panel",
        "menu_add_ext": "Add Protected Extension…",
        "menu_capture": "Capture Current Associations as Baseline",
        "menu_status": "Show Current Status",
        "menu_force_restore": "Force Restore All",
        "menu_switch_lang": "切换到中文 / Switch to Chinese",
        "menu_exit": "Exit",

        # Control Panel
        "panel_title": "WinAssocGuard Control Panel",
        "panel_subtitle": "Protected extensions (auto-restore when hijacked)",
        "tab_guard": "Guard",
        "tab_logs": "Logs",
        "tab_settings": "Settings",
        "panel_ext_label": "Extension:",
        "panel_ext_placeholder": "e.g. .pdf",
        "btn_add": "Add",
        "btn_delete": "Remove",
        "btn_delete_all": "Remove All",
        "btn_refresh": "Refresh",
        "btn_import_defaults": "Import Current Defaults",
        "btn_import_common": "Import Extensions",
        "btn_capture_selected": "Set Selected as Baseline",
        "btn_set_baseline": "Set as Baseline",
        "btn_capture_all": "Set All to Current (Baseline)",
        "btn_restore_selected": "Restore Selected",
        "btn_restore_all": "Restore All",
        "btn_edit_baseline": "Edit Baseline…",
        "btn_switch_lang": "中文/English",
        "btn_hide": "Hide to Tray",
        "btn_exit": "Exit",

        # Table columns
        "col_ext": "Extension",
        "col_base": "Baseline (App)",
        "col_curr": "Current (ProgId)",
        "col_status": "Status",
        "col_log_time": "Time",
        "col_log_event": "Event",
        "col_log_detail": "Detail",

        # Status strings
        "status_ok": "OK",
        "status_drift": "Changed",
        "status_nobase": "No baseline",

        # Dialogs / common UI
        "dlg_add_ext_title": "Add Protected Extension",
        "dlg_add_ext_prompt": "Enter an extension (e.g. .py / .docx / .pdf):",
        "dlg_invalid_ext": "Invalid extension format. Example: .pdf",
        "dlg_info_title": "Info",
        "dlg_confirm_title": "Confirm",
        "dlg_added_hint": "Added {ext}\n\nNext: manually set the default app for this extension in Windows, then click “Set All to Current (Baseline)” (or select it and click “Set Selected as Baseline”).",
        "dlg_capture_done": "Captured baseline associations for {n} extension(s).",
        "dlg_capture_none": "No valid ProgId captured.\n\nPlease set the default app manually first, then capture again.",
        "dlg_force_restore_done": "Force restore finished: processed {n} extension(s).",
        "dlg_status_title": "Current Guard Status",
        "dlg_status_col_ext": "Extension",
        "dlg_status_col_base": "Saved Baseline (ProgId)",
        "dlg_status_col_curr": "Current (ProgId)",
        "dlg_refresh": "Refresh",
        "dlg_close": "Close",

        # Panel messages
        "msg_no_selection": "Please select at least one row.",
        "msg_import_none": "No extensions with a per-user default (UserChoice) were found.\n\nYou can add extensions manually and then click “Set All to Current (Baseline)”.",
        "msg_import_none_valid": "Found {found} extension(s), but none had a valid ProgId (apps may have been uninstalled).",
        "msg_import_confirm": "Detected {n} extension(s) with per-user defaults (UserChoice).\n\nImport them and capture as baseline now?\n(Recommended to guard 5–20; you can remove extras later.)",
        "msg_import_done": "Import finished: found {found}, imported {imported} (newly added {added}), skipped {skipped} invalid.",
        "msg_select_one": "Please select exactly one row.",
        "msg_deleted": "Removed {n} item(s).",
        "msg_capture_sel_done": "Captured baseline for selected: {n} item(s).",
        "msg_capture_sel_none": "No valid ProgId captured for the selection.\n\nPlease set the default app in Windows first.",
        "msg_restore_sel_done": "Restore finished: processed {n}, succeeded {ok}.",
        "msg_confirm_delete": "Remove the selected {n} item(s)?\n\n{exts}",
        "msg_confirm_delete_all": "Remove all {n} items?\n\nThis will clear the guard list and all saved baselines.",
        "msg_delete_all_empty": "There are no protected extensions.",
        "msg_deleted_all": "Removed all {n} item(s).",
        "msg_log_count": "{n} row(s)",
        "msg_invalid_interval": "Monitor interval must be a number between 1 and 60 seconds.",
        "msg_settings_saved": "Settings saved (monitor interval {sec} seconds).",
        "msg_settings_hint": "Changes apply immediately.",
        "msg_settings_changed_detail": "interval={sec}s, notify={notify}, guard={auto}, startup={start}",
        "msg_startup_toggle_failed": "Failed to update startup setting: {msg}",
        "msg_log_restore_detail": "restore {prev} -> {base}",

        "msg_import_common_none": "Please select at least one extension.",
        "msg_import_common_done": "Import finished: selected {selected}, newly added {added}, captured {captured} baseline(s), skipped {invalid} invalid.",
        "msg_edit_baseline_prompt": "Enter a new baseline ProgId for {ext} (leave empty to clear):",
        "msg_invalid_progid": "Invalid or missing ProgId: {progid}",
        "msg_baseline_cleared": "Baseline cleared for {ext}.",
        "msg_baseline_set": "Baseline updated for {ext}.",
        "msg_hidden_to_tray": "Hidden to tray. Guarding continues in the background.",
        "msg_open_baseline_no_base": "{ext} has no baseline yet.",
        "msg_open_baseline_no_target": "Cannot resolve executable for this baseline: {progid}",
        "msg_open_baseline_failed": "Failed to open: {target}\n{msg}",
        "msg_pick_app_required": "Please choose an app from the list first.",
        "msg_manual_progid_required": "Enter a ProgId first, or disable manual mode and choose an app.",

        # Import common dialog
        "dlg_import_common_title": "Import Common Extensions",
        "dlg_import_common_desc": "Select common extensions to guard. You can import first and remove extras later.",
        "dlg_import_common_manual": "Manual input",
        "dlg_import_common_manual_hint": "Enter extensions (e.g. .mov .mkv), separated by commas, semicolons, or spaces.",
        "dlg_import_common_presets": "Quick presets",
        "dlg_import_common_list": "Common extension list",
        "preset_docs": "Documents",
        "preset_images": "Images",
        "preset_code": "Code",
        "preset_archives": "Archives",
        "preset_audio": "Audio",
        "preset_video": "Video",
        "btn_select_all": "Select All",
        "btn_select_none": "Select None",
        "chk_capture_after_import": "Capture current associations as baseline after import",
        "btn_import": "Import",
        "btn_confirm_import": "Confirm Import",
        "btn_cancel": "Cancel",

        # Notifications
        "ntf_title": "WinAssocGuard",
        "ntf_auto_restore_ok": "Auto-restore succeeded: {exts}",
        "ntf_auto_restore_fail": "Auto-restore failed: {exts}",
        "ntf_capture_ok": "Capture succeeded: {n} item(s)",
        "ntf_import_done": "Imported & captured: {n}",
        "ntf_import_common_done": "Imported common extensions: {n}",
        "ntf_force_restore_ok": "Force restore done: {n} item(s)",
        "ntf_added": "Protected extension added: {ext}",
        "ntf_hidden": "Hidden to tray (still guarding in background).",
        "ntf_error": "Error: {msg}",

        "lbl_log_filter": "Filter by ext:",
        "lbl_log_limit": "Recent:",
        "grp_settings_guard": "Guard Settings",
        "lbl_settings_interval": "Monitor interval",
        "lbl_settings_seconds": "sec",
        "chk_settings_notifications": "Enable system notifications",
        "chk_settings_guard_enabled": "Enable guard (auto restore)",
        "chk_settings_auto_start": "Launch at startup",
        "btn_apply_settings": "Apply Settings",

        "btn_confirm": "Confirm",
        "btn_clear_baseline": "Clear Baseline",
        "dlg_edit_baseline_title": "Edit Baseline: {ext}",
        "dlg_edit_baseline_desc": "Select an app for {ext} as baseline.",
        "dlg_edit_baseline_candidates": "Available apps",
        "dlg_edit_baseline_candidates_empty": "No app candidates. Enable manual mode to enter ProgId.",
        "dlg_edit_baseline_manual": "Manual ProgId (Advanced)",
        "chk_show_manual_progid": "Enter ProgId manually (Advanced)",

        "log_event_ext_added": "Added protected extension",
        "log_event_ext_deleted": "Removed protected extension",
        "log_event_deleted_all": "Removed all protected extensions",
        "log_event_imported_ext": "Imported extension",
        "log_event_capture_selected": "Captured selected baseline",
        "log_event_capture_all": "Captured all baselines",
        "log_event_import_defaults": "Imported current defaults",
        "log_event_restore_ok": "Manual restore succeeded",
        "log_event_restore_failed": "Manual restore failed",
        "log_event_baseline_set": "Baseline updated",
        "log_event_baseline_cleared": "Baseline cleared",
        "log_event_auto_restore_ok": "Auto restore succeeded",
        "log_event_auto_restore_failed": "Auto restore failed",
        "log_event_settings_updated": "Settings updated",

        # Errors / Warnings
        "warn_windows_only": "This app is Windows-only.",
    },
}


def t(lang: str, key: str, **kwargs: Any) -> str:
    """
    Translate `key` under `lang`, formatting with kwargs.
    Falls back to English, then to key itself.
    """
    lang_map = _TRANSLATIONS.get(lang) or _TRANSLATIONS[LANG_EN]
    template = lang_map.get(key) or _TRANSLATIONS[LANG_EN].get(key) or key
    try:
        return template.format(**kwargs)
    except Exception:
        # Never let i18n formatting crash the app.
        return template

