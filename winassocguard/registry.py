# -*- coding: utf-8 -*-
"""
Windows registry utilities for reading/restoring file associations.

Important note (Windows 8+):
- Writing to the `UserChoice` key directly is blocked by a hash mechanism.
- This project avoids that by:
  1) saving a baseline ProgId, and
  2) setting HKCU\Software\Classes\.ext default to that ProgId, and
  3) deleting UserChoice so Windows falls back to HKCU\Software\Classes.
This works in many real-world cases, but Windows can be stubborn in some setups.
"""

from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

if sys.platform != "win32":
    raise RuntimeError("Windows-only module")

import winreg

# SHChangeNotify constants
SHCNE_ASSOCCHANGED = 0x08000000
SHCNF_IDLIST = 0x0000


_EXT_RE = re.compile(r"^\.[A-Za-z0-9][A-Za-z0-9._+\-]*$")


def normalize_ext(ext: str) -> str:
    ext = (ext or "").strip()
    if not ext:
        return ""
    if not ext.startswith("."):
        ext = "." + ext
    return ext.lower()


def is_valid_ext(ext: str) -> bool:
    ext = normalize_ext(ext)
    return bool(_EXT_RE.match(ext))


def _read_value(root, subkey: str, value_name: str) -> Optional[str]:
    if value_name == "":
        value_name = None
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ) as k:
            val, _typ = winreg.QueryValueEx(k, value_name)
            if isinstance(val, str) and val.strip():
                return val.strip()
            return None
    except FileNotFoundError:
        return None
    except OSError:
        return None


def _has_value_name(root, subkey: str, value_name: str) -> bool:
    if value_name == "":
        value_name = None
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ) as k:
            winreg.QueryValueEx(k, value_name)
            return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def _extract_exe_from_command(command: str) -> Optional[str]:
    """
    Best effort to extract the executable path/name from a command string.
    """
    if not isinstance(command, str):
        return None
    s = command.strip()
    if not s:
        return None

    # Quoted executable path
    if s[0] == '"':
        end = s.find('"', 1)
        if end > 1:
            exe = s[1:end].strip()
            if exe:
                return Path(exe).name

    # Unquoted first token
    token = s.split()[0]
    if token:
        try:
            p = Path(token)
            if p.suffix:
                return p.name
        except Exception:
            return token

    return None


def _resolve_resource_string(value: str) -> Optional[str]:
    """
    Resolve values like '@%SystemRoot%\\system32\\shell32.dll,-22033'.
    """
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s.startswith("@"):
        return None

    try:
        import ctypes
        import ctypes.wintypes as wt

        shlwapi = ctypes.WinDLL("Shlwapi", use_last_error=True)
        load_str = shlwapi.SHLoadIndirectStringW
        load_str.argtypes = [wt.LPCWSTR, wt.LPWSTR, wt.UINT, wt.LPVOID]
        load_str.restype = ctypes.HRESULT

        # Expected format: @path,-id
        required = 1024
        buf = ctypes.create_unicode_buffer(required)
        hr = load_str(s, buf, required, None)
        if hr == 0:
            txt = (buf.value or "").strip()
            return txt or None
    except Exception:
        return None
    return None


def _assoc_query_friendly_name(progid_or_ext: str) -> Optional[str]:
    """
    Use Windows shell association API to get a friendly handler name.
    This often gives a readable app name for both desktop and UWP-like IDs.
    """
    try:
        import ctypes
        import ctypes.wintypes as wt

        shlwapi = ctypes.WinDLL("Shlwapi", use_last_error=True)
        query = shlwapi.AssocQueryStringW
        query.argtypes = [
            wt.DWORD,  # ASSOCF
            wt.DWORD,  # ASSOCSTR
            wt.LPCWSTR,  # pszAssoc
            wt.LPCWSTR,  # pszExtra
            wt.LPWSTR,  # pszOut
            wt.LPDWORD,  # pcchOut
        ]
        query.restype = ctypes.HRESULT

        ASSOCF_NONE = 0
        ASSOCSTR_FRIENDLYAPPNAME = 4

        required = wt.DWORD(0)
        hr = query(ASSOCF_NONE, ASSOCSTR_FRIENDLYAPPNAME, progid_or_ext, "open", None, ctypes.byref(required))
        if hr not in (0, 1):  # not S_OK / S_FALSE
            return None

        if not required.value:
            return None
        buf = ctypes.create_unicode_buffer(required.value)
        hr = query(ASSOCF_NONE, ASSOCSTR_FRIENDLYAPPNAME, progid_or_ext, "open", buf, ctypes.byref(required))
        if hr != 0:
            return None
        txt = (buf.value or "").strip()
        return txt or None
    except Exception:
        return None


def get_progid_display_name(progid: str) -> str:
    """
    Return a human-friendly program name for a ProgId.
    Fallbacks keep working even when shell apps expose less metadata.
    """
    progid = (progid or "").strip()
    if not progid:
        return ""

    # Common location for a readable name.
    display = _read_default_value(winreg.HKEY_CLASSES_ROOT, progid)
    if display:
        resolved = _resolve_resource_string(display)
        if resolved:
            return resolved
        return display

    # Shell API often resolves this better than raw registry lookup for modern apps.
    shell = _assoc_query_friendly_name(progid)
    if shell:
        return shell

    # Some registrations expose FriendlyTypeName in a known value.
    display = _read_value(winreg.HKEY_CLASSES_ROOT, progid, "FriendlyTypeName")
    if display:
        return display

    # Fallback: parse open command executable name, e.g. chrome.exe / path.
    for suffix in ("shell\\open\\command", "shell\\Open\\command"):
        cmd = _read_value(winreg.HKEY_CLASSES_ROOT, f"{progid}\\{suffix}", "")
        if cmd:
            exe = _extract_exe_from_command(cmd)
            if exe:
                return exe

    return progid


def get_progid_app_name(progid: str) -> str:
    """
    Best-effort app name for a ProgId, preferring Windows association metadata.
    """
    progid = (progid or "").strip()
    if not progid:
        return ""

    shell = _assoc_query_friendly_name(progid)
    if shell and shell != progid:
        return shell

    if progid.lower().startswith("applications\\"):
        app = progid.split("\\", 1)[-1].strip()
        if app:
            return app

    for suffix in ("shell\\open\\command", "shell\\Open\\command"):
        cmd = _read_value(winreg.HKEY_CLASSES_ROOT, f"{progid}\\{suffix}", "")
        if cmd:
            exe = _extract_exe_from_command(cmd)
            if exe:
                return exe

    return ""


def format_progid_for_picker(progid: str) -> str:
    """
    Display used in app picker: prefer app name, then file-type name.
    """
    progid = (progid or "").strip()
    if not progid:
        return ""
    app = get_progid_app_name(progid)
    typ = get_progid_display_name(progid)
    if app and typ and app.lower() != typ.lower():
        return f"{app} - {typ}"
    return app or typ or progid


def format_progid_for_display(progid: str) -> str:
    """
    Display value used in UI: Friendly name + original ID for traceability.
    """
    progid = (progid or "").strip()
    if not progid:
        return ""
    friendly = format_progid_for_picker(progid)
    if friendly and friendly != progid:
        return f"{friendly} ({progid})"
    return progid


def _list_value_names(root, subkey: str) -> list[str]:
    out: list[str] = []
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ) as k:
            i = 0
            while True:
                try:
                    name, _val, _typ = winreg.EnumValue(k, i)
                    i += 1
                except OSError:
                    break
                if isinstance(name, str) and name.strip():
                    out.append(name.strip())
    except Exception:
        return []
    return out


def _list_string_values(root, subkey: str) -> list[str]:
    out: list[str] = []
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ) as k:
            i = 0
            while True:
                try:
                    _name, val, _typ = winreg.EnumValue(k, i)
                    i += 1
                except OSError:
                    break
                if isinstance(val, str) and val.strip():
                    out.append(val.strip())
    except Exception:
        return []
    return out


def _list_subkeys(root, subkey: str) -> list[str]:
    out: list[str] = []
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ) as k:
            i = 0
            while True:
                try:
                    name = winreg.EnumKey(k, i)
                    i += 1
                except OSError:
                    break
                if isinstance(name, str) and name.strip():
                    out.append(name.strip())
    except Exception:
        return []
    return out


def list_candidate_progids_for_ext(ext: str, limit: int = 24) -> list[str]:
    """
    Collect likely ProgId candidates for a file extension from common registry locations.
    """
    ext = normalize_ext(ext)
    if not is_valid_ext(ext):
        return []

    seen: set[str] = set()
    out: list[str] = []

    def add_candidate(progid: Optional[str]) -> None:
        p = (progid or "").strip()
        if not p or p in seen:
            return
        # Keep only resolvable ProgId-like entries.
        if not is_progid_valid(p):
            return
        seen.add(p)
        out.append(p)

    # Current effective chain first.
    add_candidate(get_userchoice_progid(ext))
    add_candidate(get_hkcu_classes_progid(ext))
    add_candidate(get_hkcr_progid(ext))

    # Windows "Open with" MRU ProgIds (value names are ProgIds).
    add_candidate_list = _list_value_names(
        winreg.HKEY_CURRENT_USER,
        fr"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{ext}\OpenWithProgids",
    )
    for progid in add_candidate_list:
        add_candidate(progid)

    # Global extension-level OpenWithProgids.
    add_candidate_list = _list_value_names(winreg.HKEY_CLASSES_ROOT, fr"{ext}\OpenWithProgids")
    for progid in add_candidate_list:
        add_candidate(progid)

    # OpenWithList stores executable names; map them to Applications\<exe>.
    for exe in _list_string_values(
        winreg.HKEY_CURRENT_USER,
        fr"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{ext}\OpenWithList",
    ):
        add_candidate(fr"Applications\{exe}")
    for exe in _list_string_values(winreg.HKEY_CLASSES_ROOT, fr"{ext}\OpenWithList"):
        add_candidate(fr"Applications\{exe}")

    # Registered applications that explicitly list this extension.
    if len(out) < max(1, int(limit)):
        for app_name in _list_subkeys(winreg.HKEY_CLASSES_ROOT, "Applications"):
            if len(out) >= max(1, int(limit)):
                break
            supported_types_key = fr"Applications\{app_name}\SupportedTypes"
            if _has_value_name(winreg.HKEY_CLASSES_ROOT, supported_types_key, ext):
                add_candidate(fr"Applications\{app_name}")

    return out[: max(1, int(limit))]


def list_user_fileexts(only_userchoice: bool = True) -> list[str]:
    '''
    Enumerate file extensions from:
      HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts

    - If `only_userchoice` is True (default), return only extensions that have a
      `UserChoice` subkey (meaning the user explicitly set a default app at least once).

    This is useful for a one-click "import my current defaults" UX.
    '''
    base = r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts"
    out: list[str] = []
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base, 0, winreg.KEY_READ) as k:
            i = 0
            while True:
                try:
                    name = winreg.EnumKey(k, i)
                    i += 1
                except OSError:
                    break

                if not name or not name.startswith('.'):
                    continue

                extn = normalize_ext(name)
                if not is_valid_ext(extn):
                    continue

                if only_userchoice:
                    uc = base + "\\" + name + "\\UserChoice"
                    if not _key_exists(winreg.HKEY_CURRENT_USER, uc):
                        continue

                out.append(extn)
    except Exception:
        return []

    return sorted(set(out))

def _read_default_value(root, subkey: str) -> Optional[str]:
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ) as k:
            try:
                val, _typ = winreg.QueryValueEx(k, None)  # default value
            except FileNotFoundError:
                return None
            if isinstance(val, str) and val.strip():
                return val.strip()
            return None
    except FileNotFoundError:
        return None
    except OSError:
        return None


def _key_exists(root, subkey: str) -> bool:
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ):
            return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def get_userchoice_progid(ext: str) -> Optional[str]:
    ext = normalize_ext(ext)
    if not ext:
        return None
    subkey = fr"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{ext}\UserChoice"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey, 0, winreg.KEY_READ) as k:
            val, _typ = winreg.QueryValueEx(k, "ProgId")
            if isinstance(val, str) and val.strip():
                return val.strip()
            return None
    except FileNotFoundError:
        return None
    except OSError:
        return None


def get_hkcu_classes_progid(ext: str) -> Optional[str]:
    ext = normalize_ext(ext)
    if not ext:
        return None
    subkey = fr"Software\Classes\{ext}"
    return _read_default_value(winreg.HKEY_CURRENT_USER, subkey)


def get_hkcr_progid(ext: str) -> Optional[str]:
    ext = normalize_ext(ext)
    if not ext:
        return None
    subkey = ext  # under HKCR
    return _read_default_value(winreg.HKEY_CLASSES_ROOT, subkey)


def get_effective_progid(ext: str) -> Optional[str]:
    """
    Best-effort: UserChoice -> HKCU\Software\Classes -> HKCR
    """
    ext = normalize_ext(ext)
    if not ext:
        return None
    uc = get_userchoice_progid(ext)
    if uc:
        return uc
    hkcu = get_hkcu_classes_progid(ext)
    if hkcu:
        return hkcu
    return get_hkcr_progid(ext)


def is_progid_valid(progid: str) -> bool:
    progid = (progid or "").strip()
    if not progid:
        return False
    # ProgId keys typically live under HKCR\<ProgId>
    return _key_exists(winreg.HKEY_CLASSES_ROOT, progid)


def set_hkcu_classes_ext_default(ext: str, progid: str) -> None:
    ext = normalize_ext(ext)
    progid = (progid or "").strip()
    if not ext or not progid:
        return
    subkey = fr"Software\Classes\{ext}"
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, subkey, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, None, 0, winreg.REG_SZ, progid)


def _delete_key_tree(root, subkey: str) -> None:
    """
    Recursively delete a key. If it doesn't exist, do nothing.
    """
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ | winreg.KEY_WRITE) as k:
            # Enumerate subkeys first
            while True:
                try:
                    child = winreg.EnumKey(k, 0)
                    _delete_key_tree(root, subkey + "\\" + child)
                except OSError:
                    break
    except FileNotFoundError:
        return
    except OSError:
        # If we can't open it, try deleting directly.
        pass

    # Now delete this key
    try:
        winreg.DeleteKey(root, subkey)
    except FileNotFoundError:
        return
    except OSError:
        # Sometimes it still has subkeys due to races; retry a few times.
        for _ in range(3):
            time.sleep(0.05)
            try:
                winreg.DeleteKey(root, subkey)
                return
            except Exception:
                continue


def delete_userchoice(ext: str) -> None:
    ext = normalize_ext(ext)
    if not ext:
        return
    subkey = fr"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{ext}\UserChoice"
    _delete_key_tree(winreg.HKEY_CURRENT_USER, subkey)


def broadcast_assoc_changed() -> None:
    """
    Notify the shell that associations changed.
    """
    # Try pywin32 first
    try:
        import win32gui  # type: ignore

        win32gui.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
        return
    except Exception:
        pass

    # Fallback: ctypes
    try:
        import ctypes
        import ctypes.wintypes as wt

        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        shell32.SHChangeNotify.argtypes = [wt.LONG, wt.UINT, wt.LPVOID, wt.LPVOID]
        shell32.SHChangeNotify.restype = None
        shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
    except Exception:
        # Ignore; shell will catch up eventually.
        pass


@dataclass
class RestoreResult:
    ext: str
    ok: bool
    error: Optional[str] = None
    previous_progid: Optional[str] = None
    baseline_progid: Optional[str] = None


def restore_to_baseline(ext: str, baseline_progid: str) -> RestoreResult:
    """
    Restore an extension's association to baseline:

    1) Set HKCU\Software\Classes\.ext default -> baseline ProgId
    2) Delete UserChoice to remove per-user override
    3) Broadcast association change
    """
    ext = normalize_ext(ext)
    baseline_progid = (baseline_progid or "").strip()
    prev = None
    try:
        prev = get_effective_progid(ext)
        if not ext or not baseline_progid:
            return RestoreResult(ext=ext, ok=False, error="invalid_args", previous_progid=prev, baseline_progid=baseline_progid)

        set_hkcu_classes_ext_default(ext, baseline_progid)
        delete_userchoice(ext)
        broadcast_assoc_changed()
        # Re-check
        now = get_effective_progid(ext)
        ok = (now == baseline_progid) or (now is None)  # None can happen transiently
        return RestoreResult(ext=ext, ok=ok, error=None if ok else "mismatch_after_restore", previous_progid=prev, baseline_progid=baseline_progid)
    except Exception as e:
        return RestoreResult(ext=ext, ok=False, error=str(e), previous_progid=prev, baseline_progid=baseline_progid)
