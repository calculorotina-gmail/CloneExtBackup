"""
Chrome Detector and Profile Scanner for Windows.
Robustly discovers Chrome User Data, all configured profiles (Default, Profile 1, 2, ...),
and discovers installed extensions with full metadata, local directory paths, sizes,
file counts, enabled states, and localized names.
"""

import os
import glob
import json
import base64
import winreg
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from .disk_space import calculate_dir_size_and_count, format_bytes


def get_default_chrome_user_data_path() -> str:
    """Returns standard Windows Chrome User Data directory path."""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        candidate = os.path.join(local_app_data, "Google", "Chrome", "User Data")
        if os.path.exists(candidate):
            return candidate
    
    # Fallback to user home
    user_home = os.path.expanduser("~")
    candidate = os.path.join(user_home, "AppData", "Local", "Google", "Chrome", "User Data")
    return candidate


def get_installed_chrome_version() -> str:
    """Detects installed Google Chrome version via Windows Registry or executable."""
    # Check 64-bit and 32-bit registry keys
    reg_paths = [
        (winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Google\Chrome\BLBeacon"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Google\Chrome\BLBeacon")
    ]
    for hkey, subkey in reg_paths:
        try:
            with winreg.OpenKey(hkey, subkey) as k:
                val, _ = winreg.QueryValueEx(k, "version")
                if val:
                    return str(val)
        except Exception:
            continue
    return "Desconhecida (Chrome instalado)"


def resolve_extension_localized_name(ext_dir: str, manifest: dict, fallback_name: str) -> str:
    """
    Resolves localized extension names (e.g. __MSG_appName__ or __MSG_extension_name__)
    by reading messages.json from _locales/ in priority order (pt, default_locale, en).
    """
    name = manifest.get("name", fallback_name)
    if not name or not name.startswith("__MSG_") or not name.endswith("__"):
        return name

    key = name[6:-2]
    locales_dir = os.path.join(ext_dir, "_locales")
    if not os.path.exists(locales_dir):
        return name

    # Preferred locale check order
    preferred = ["pt_PT", "pt_BR", "pt"]
    default_loc = manifest.get("default_locale")
    if default_loc and default_loc not in preferred:
        preferred.append(default_loc)
    if "en" not in preferred:
        preferred.extend(["en_US", "en_GB", "en"])

    lower_key = key.lower()

    for loc in preferred:
        msg_file = os.path.join(locales_dir, loc, "messages.json")
        if os.path.exists(msg_file):
            try:
                with open(msg_file, "r", encoding="utf-8", errors="ignore") as f:
                    msgs = json.load(f)
                    for k, v in msgs.items():
                        if k.lower() == lower_key and isinstance(v, dict) and "message" in v:
                            return v["message"]
            except Exception:
                continue

    # Search any available locale as fallback
    try:
        for loc_entry in os.listdir(locales_dir):
            msg_file = os.path.join(locales_dir, loc_entry, "messages.json")
            if os.path.exists(msg_file):
                with open(msg_file, "r", encoding="utf-8", errors="ignore") as f:
                    msgs = json.load(f)
                    for k, v in msgs.items():
                        if k.lower() == lower_key and isinstance(v, dict) and "message" in v:
                            return v["message"]
    except Exception:
        pass

    return name


def extract_extension_icon_as_data_url(ext_dir: str, manifest: dict) -> Optional[str]:
    """Reads extension icon from manifest and returns a base64 Data URL for UI rendering."""
    icons = manifest.get("icons", {})
    if not isinstance(icons, dict) or not icons:
        return None

    # Pick largest available icon (128 -> 48 -> 32 -> 16)
    icon_rel = icons.get("128") or icons.get("48") or icons.get("32") or icons.get("16")
    if not icon_rel:
        for v in icons.values():
            if isinstance(v, str):
                icon_rel = v
                break

    if not icon_rel:
        return None

    icon_path = os.path.join(ext_dir, icon_rel.replace("/", os.sep))
    if os.path.exists(icon_path) and os.path.isfile(icon_path):
        try:
            ext = os.path.splitext(icon_path)[1].lower().strip(".")
            mime = "image/png" if ext == "png" else ("image/jpeg" if ext in ("jpg", "jpeg") else "image/svg+xml")
            with open(icon_path, "rb") as f:
                data = f.read()
                if len(data) <= 200000:  # Max 200KB for icon payload
                    b64 = base64.b64encode(data).decode("ascii")
                    return f"data:{mime};base64,{b64}"
        except Exception:
            return None
    return None


class ChromeDetector:
    def __init__(self, custom_user_data_path: Optional[str] = None):
        self.user_data_path = custom_user_data_path or get_default_chrome_user_data_path()

    def set_custom_path(self, path: str):
        if path and os.path.exists(path):
            self.user_data_path = path

    def is_user_data_valid(self) -> bool:
        return os.path.exists(self.user_data_path) and os.path.isdir(self.user_data_path)

    def detect_profiles(self) -> List[Dict[str, Any]]:
        """
        Discovers all Chrome profiles in User Data (Default, Profile 1, Profile 2, etc.)
        and maps them to human-readable names from Local State.
        """
        profiles = []
        if not self.is_user_data_valid():
            return profiles

        # Read Local State profile cache if available
        names_map = {}
        local_state_path = os.path.join(self.user_data_path, "Local State")
        if os.path.exists(local_state_path):
            try:
                with open(local_state_path, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                    info_cache = data.get("profile", {}).get("info_cache", {})
                    for prof_dir, info in info_cache.items():
                        name = info.get("name") or prof_dir
                        gaia_name = info.get("gaia_name")
                        disp = f"{name} ({gaia_name})" if gaia_name and gaia_name != name else name
                        names_map[prof_dir] = disp
            except Exception:
                pass

        # Scan for candidate profile directories
        candidate_dirs = ["Default"]
        for item in os.listdir(self.user_data_path):
            full_p = os.path.join(self.user_data_path, item)
            if os.path.isdir(full_p) and (item.startswith("Profile ") or item == "Guest Profile"):
                if item not in candidate_dirs:
                    candidate_dirs.append(item)

        for p_dir in candidate_dirs:
            full_prof_path = os.path.join(self.user_data_path, p_dir)
            if not os.path.exists(full_prof_path):
                continue

            ext_path = os.path.join(full_prof_path, "Extensions")
            ext_count = 0
            if os.path.exists(ext_path) and os.path.isdir(ext_path):
                ext_count = len([x for x in os.listdir(ext_path) if os.path.isdir(os.path.join(ext_path, x))])

            friendly_name = names_map.get(p_dir, "Pessoa 1" if p_dir == "Default" else p_dir)
            profiles.append({
                "profile_id": p_dir,
                "name": friendly_name,
                "path": full_prof_path,
                "extensions_path": ext_path,
                "extensions_count": ext_count,
                "is_default": (p_dir == "Default")
            })

        return profiles

    def get_extension_states_from_preferences(self, profile_id: str) -> Dict[str, Dict[str, Any]]:
        """Reads Secure Preferences or Preferences to determine enabled/disabled extension states."""
        states = {}
        prof_path = os.path.join(self.user_data_path, profile_id)
        
        pref_candidates = [
            os.path.join(prof_path, "Secure Preferences"),
            os.path.join(prof_path, "Preferences")
        ]

        for pfile in pref_candidates:
            if os.path.exists(pfile):
                try:
                    with open(pfile, "r", encoding="utf-8", errors="ignore") as f:
                        data = json.load(f)
                        settings = data.get("extensions", {}).get("settings", {})
                        for ext_id, ext_info in settings.items():
                            if ext_id not in states:
                                raw_state = ext_info.get("state")
                                disable_reasons = ext_info.get("disable_reasons", 0)
                                # 1 = Enabled, 0 = Disabled
                                is_enabled = (raw_state == 1 or raw_state is None) and (disable_reasons == 0)
                                states[ext_id] = {
                                    "enabled": is_enabled,
                                    "disable_reasons": disable_reasons,
                                    "install_time": ext_info.get("install_time"),
                                    "location": ext_info.get("location"),
                                    "manifest_name": ext_info.get("manifest", {}).get("name")
                                }
                except Exception:
                    continue
        return states

    def get_installed_extensions(self, profile_id: str = "Default") -> List[Dict[str, Any]]:
        """
        Discovers all physical extension installations within a given profile,
        parsing manifest.json, calculating size, file count, and enabled status.
        """
        results = []
        prof_path = os.path.join(self.user_data_path, profile_id)
        ext_base_dir = os.path.join(prof_path, "Extensions")
        
        if not os.path.exists(ext_base_dir):
            return results

        states_map = self.get_extension_states_from_preferences(profile_id)

        try:
            ext_ids = [d for d in os.listdir(ext_base_dir) if os.path.isdir(os.path.join(ext_base_dir, d))]
        except Exception:
            return results

        for ext_id in ext_ids:
            ext_id_dir = os.path.join(ext_base_dir, ext_id)
            try:
                # Inside <ext_id> folder are version directories (e.g. "1.0.0_0")
                versions = [v for v in os.listdir(ext_id_dir) if os.path.isdir(os.path.join(ext_id_dir, v))]
            except Exception:
                continue

            if not versions:
                continue

            # Sort versions or take latest
            versions.sort(reverse=True)
            active_version_dir = versions[0]
            full_version_path = os.path.join(ext_id_dir, active_version_dir)

            manifest_path = os.path.join(full_version_path, "manifest.json")
            manifest_data = {}
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8", errors="ignore") as mf:
                        manifest_data = json.load(mf)
                except Exception:
                    manifest_data = {}

            # Resolve name
            st_info = states_map.get(ext_id, {})
            raw_name = manifest_data.get("name", ext_id)
            display_name = resolve_extension_localized_name(full_version_path, manifest_data, raw_name)
            if display_name.startswith("__MSG_") and st_info.get("manifest_name"):
                display_name = st_info["manifest_name"]
            manifest_version = manifest_data.get("version", active_version_dir.split("_")[0])

            # Calculate physical directory metrics
            size_bytes, file_count = calculate_dir_size_and_count(full_version_path)
            
            # Modification date
            try:
                mtime = os.path.getmtime(full_version_path)
                mtime_str = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                mtime_str = "Desconhecida"

            # Determine state: Ativa, Desativada, Erro
            st_info = states_map.get(ext_id, {})
            is_enabled = st_info.get("enabled", True)
            status_text = "Ativa" if is_enabled else "Desativada"

            icon_url = extract_extension_icon_as_data_url(full_version_path, manifest_data)

            results.append({
                "extension_id": ext_id,
                "name": display_name,
                "version": manifest_version,
                "version_dir": active_version_dir,
                "profile_id": profile_id,
                "status": status_text,
                "is_enabled": is_enabled,
                "local_path": full_version_path,
                "size_bytes": size_bytes,
                "size_formatted": format_bytes(size_bytes),
                "file_count": file_count,
                "modified_date": mtime_str,
                "description": manifest_data.get("description", ""),
                "manifest_version": manifest_data.get("manifest_version", 3),
                "permissions": manifest_data.get("permissions", []),
                "icon_url": icon_url
            })

        # Sort alphabetically by name
        results.sort(key=lambda x: x["name"].lower())
        return results
