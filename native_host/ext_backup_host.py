#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Chrome Native Messaging Host for Chrome Extension Backup Pro.
Communicates with the Chrome Extension via standard 32-bit framed JSON over stdin/stdout.
Processes physical backup, restore, validation, comparison, scheduling, and profile discovery.
"""

import sys
import os
import json
import struct
import platform
import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure core package and native_host are on Python sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from core.logger import logger
from core.error_codes import create_error_response, ERROR_DEFINITIONS
from core.disk_space import get_disk_free_space, format_bytes
from core.process_manager import is_chrome_running, request_graceful_chrome_close
from core.license_manager import license_mgr, validate_license_key_format, generate_sample_license_key
from core.chrome_detector import (
    ChromeDetector,
    get_default_chrome_user_data_path,
    get_installed_chrome_version
)
from core.integrity import validate_archive_integrity
from core.compressor import BackupCompressor
from core.encryption import is_file_encrypted
from core.backup_engine import BackupEngine, get_default_backup_dir
from core.restore_engine import RestoreEngine, DEFAULT_ROLLBACKS_DIR
from core.comparator import compare_two_versions
from core.scheduler import get_schedule_config, save_schedule_config, register_windows_task, unregister_windows_task

HOST_VERSION = "2.0.0"
CONFIG_FILE = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "ChromeExtBackupPro",
    "config.json"
)
HISTORY_FILE = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "ChromeExtBackupPro",
    "history.json"
)


def load_app_settings() -> Dict[str, Any]:
    """Loads persistent settings or default configuration."""
    defaults = {
        "primary_backup_dir": get_default_backup_dir(),
        "secondary_backup_dir": "",
        "auto_secondary_backup": False,
        "compression_level": 6,
        "is_incremental": True,
        "encryption_enabled": False,
        "encryption_password": "",
        "theme": "system",
        "language": "pt",
        "notify_on_success": True,
        "notify_on_error": True,
        "notify_on_change": True,
        "confirm_before_restore": True,
        "create_rollback_before_restore": True,
        "retention_max_versions": 5,
        "retention_days": 30,
        "custom_chrome_user_data": "",
        "auto_close_chrome_on_restore": False
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                defaults.update(saved)
        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {e}", "SETTINGS")
    return defaults


def save_app_settings(settings: Dict[str, Any]) -> bool:
    """Persists settings dictionary to config file."""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        # Avoid saving plaintext password in config if user prefers
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Erro ao gravar configurações: {e}", "SETTINGS")
        return False


def load_history() -> list:
    """Loads audit history of operations (Backup, Restore, Rollback, Validate, Delete)."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def record_history_entry(action: str, ext_name: str, ext_id: str, profile_id: str, version: str, result: str, errors: str = ""):
    """Appends an entry to the audit history file."""
    try:
        entries = load_history()
        entry = {
            "id": f"hist_{int(datetime.datetime.now().timestamp()*1000)}",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,  # Backup, Restore, Rollback, Validation, Delete
            "extension_name": ext_name,
            "extension_id": ext_id,
            "profile_id": profile_id,
            "version": version,
            "result": result,  # Sucesso, Falha, Avisos
            "errors": errors
        }
        entries.insert(0, entry)
        # Keep last 500 operations
        entries = entries[:500]
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
    except Exception as e:
        logger.error(f"Erro ao registar histórico: {e}", "HISTORY")


class HostCommandHandler:
    def __init__(self):
        self.settings = load_app_settings()
        self.detector = ChromeDetector(self.settings.get("custom_chrome_user_data") or None)
        self.backup_engine = BackupEngine(self.settings.get("primary_backup_dir"))
        self.restore_engine = RestoreEngine()

    def reload_config(self):
        self.settings = load_app_settings()
        self.detector = ChromeDetector(self.settings.get("custom_chrome_user_data") or None)
        self.backup_engine = BackupEngine(self.settings.get("primary_backup_dir"))

    def handle_ping(self, payload: dict) -> dict:
        return {
            "success": True,
            "response": "pong",
            "host_version": HOST_VERSION,
            "platform": f"{platform.system()} {platform.release()}",
            "arch": platform.machine(),
            "python_version": platform.python_version(),
            "chrome_user_data_path": self.detector.user_data_path,
            "user_data_exists": self.detector.is_user_data_valid()
        }

    def handle_get_system_info(self, payload: dict) -> dict:
        dest_dir = self.settings.get("primary_backup_dir") or get_default_backup_dir()
        disk_info = get_disk_free_space(dest_dir)
        chrome_ver = get_installed_chrome_version()
        
        return {
            "success": True,
            "os": f"Windows {platform.release()} ({platform.win32_edition() if hasattr(platform, 'win32_edition') else ''})",
            "arch": platform.machine(),
            "chrome_version": chrome_ver,
            "host_version": HOST_VERSION,
            "disk": disk_info,
            "user_data_path": self.detector.user_data_path,
            "license": license_mgr.get_info()
        }

    def handle_get_profiles(self, payload: dict) -> dict:
        profiles = self.detector.detect_profiles()
        return {
            "success": True,
            "profiles": profiles,
            "count": len(profiles)
        }

    def handle_get_extensions(self, payload: dict) -> dict:
        profile_id = payload.get("profile_id", "Default")
        extensions = self.detector.get_installed_extensions(profile_id)
        
        # Cross-reference with existing backups in primary directory
        primary_dir = self.settings.get("primary_backup_dir") or get_default_backup_dir()
        backups = self._scan_backups_in_dir(primary_dir)
        
        for ext in extensions:
            ext_id = ext["extension_id"]
            matching = [b for b in backups if b.get("extension_id") == ext_id]
            ext["backup_count"] = len(matching)
            if matching:
                # Most recent backup date
                matching.sort(key=lambda x: x.get("backup_date", ""), reverse=True)
                ext["last_backup_date"] = matching[0].get("backup_date", "Desconhecido")
                ext["last_backup_status"] = matching[0].get("integrity_status", "Válido")
                ext["has_backup"] = True
            else:
                ext["last_backup_date"] = "Nenhum backup"
                ext["last_backup_status"] = "Sem backup"
                ext["has_backup"] = False

        return {
            "success": True,
            "profile_id": profile_id,
            "extensions": extensions,
            "count": len(extensions)
        }

    def handle_check_chrome_running(self, payload: dict) -> dict:
        return is_chrome_running()

    def handle_close_chrome(self, payload: dict) -> dict:
        logger.info("Solicitação controlada de encerramento do Google Chrome autorizada pelo utilizador.", "PROCESS")
        return request_graceful_chrome_close()

    def handle_backup_extension(self, payload: dict) -> dict:
        ext_id = payload.get("extension_id")
        ext_name = payload.get("extension_name", ext_id)
        version = payload.get("version", "1.0")
        source_dir = payload.get("source_dir")
        profile_id = payload.get("profile_id", "Default")
        compression = int(payload.get("compression_level", self.settings.get("compression_level", 6)))
        is_incremental = bool(payload.get("is_incremental", self.settings.get("is_incremental", True)))
        password = payload.get("password") or (self.settings.get("encryption_password") if self.settings.get("encryption_enabled") else None)
        lock_backup = bool(payload.get("lock_backup", False))
        ignore_disk = bool(payload.get("ignore_disk_warning", False))

        primary_target = self.settings.get("primary_backup_dir") or get_default_backup_dir()
        secondary_target = self.settings.get("secondary_backup_dir") if self.settings.get("auto_secondary_backup") else None

        # Check license tier limitations
        lic = license_mgr.get_info()
        if lic["tier"] == "free":
            existing = [b for b in self._scan_backups_in_dir(primary_target)]
            if len(existing) >= lic["features"]["max_backups"]:
                return create_error_response("LC-0001", "backup", "", f"O plano Gratuito permite até {lic['features']['max_backups']} backups. Atualize para o Premium para backups ilimitados.")
            is_incremental = False
            secondary_target = None
            password = None

        res = self.backup_engine.create_backup(
            extension_id=ext_id,
            extension_name=ext_name,
            version=version,
            source_dir=source_dir,
            profile_id=profile_id,
            target_dir=primary_target,
            secondary_target_dir=secondary_target,
            compression_level=compression,
            is_incremental=is_incremental,
            password=password,
            lock_backup=lock_backup,
            ignore_disk_warning=ignore_disk
        )

        # Record history
        if res.get("success"):
            record_history_entry("Backup", ext_name, ext_id, profile_id, version, "Sucesso")
        else:
            err_msg = res.get("error", {}).get("description", "Falha na criação do backup")
            record_history_entry("Backup", ext_name, ext_id, profile_id, version, "Falha", err_msg)

        return res

    def _scan_backups_in_dir(self, directory: str) -> list:
        """Helper to scan and parse backups in a directory (.crxbackup and .zip)."""
        if not os.path.exists(directory):
            return []
        import zipfile
        backups = []
        for root, _, files in os.walk(directory):
            for f in files:
                if f.endswith(".crxbackup") or f.endswith(".zip"):
                    fp = os.path.join(root, f)
                    try:
                        encrypted = is_file_encrypted(fp)
                        mtime = os.path.getmtime(fp)
                        date_str = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                        file_size = os.path.getsize(fp)

                        manifest = {}
                        file_count = 0
                        if not encrypted:
                            try:
                                with zipfile.ZipFile(fp, "r") as z:
                                    namelist = z.namelist()
                                    file_count = len([n for n in namelist if not n.endswith("/")])
                                    if "manifest.json" in namelist:
                                        with z.open("manifest.json") as mf:
                                            manifest = json.load(mf)
                                    elif "extension/manifest.json" in namelist:
                                        with z.open("extension/manifest.json") as mf:
                                            manifest = json.load(mf)
                                    else:
                                        candidates = [n for n in namelist if n.endswith("/manifest.json")]
                                        if candidates:
                                            with z.open(candidates[0]) as mf:
                                                manifest = json.load(mf)
                            except Exception:
                                pass

                        # Check if it's a direct extension manifest or backup manifest
                        if "manifest_version" in manifest and "backup_id" not in manifest:
                            ext_name = manifest.get("name", os.path.splitext(f)[0])
                            version = manifest.get("version", "1.0")
                            ext_id = "desconhecido"
                            parts = os.path.splitext(f)[0].split("_")
                            for p in parts:
                                if len(p) == 32 and p.isalnum() and p.islower():
                                    ext_id = p
                                    break

                            backups.append({
                                "backup_id": os.path.splitext(f)[0],
                                "filename": f,
                                "path": fp,
                                "extension_id": ext_id,
                                "extension_name": ext_name,
                                "version": version,
                                "chrome_profile": "Default",
                                "backup_date": date_str,
                                "file_count": file_count,
                                "size_bytes": file_size,
                                "size_formatted": format_bytes(file_size),
                                "is_encrypted": False,
                                "is_locked": False,
                                "is_incremental": False,
                                "format": "zip",
                                "compression_level": 6,
                                "integrity_status": "Válido (Arquivo ZIP)"
                            })
                        elif f.endswith(".crxbackup") or "backup_id" in manifest:
                            backups.append({
                                "backup_id": manifest.get("backup_id", os.path.splitext(f)[0]),
                                "filename": f,
                                "path": fp,
                                "extension_id": manifest.get("extension_id", f.split("_")[1] if "_" in f else "desconhecido"),
                                "extension_name": manifest.get("extension_name", f.split("_")[0]),
                                "version": manifest.get("version", "1.0"),
                                "chrome_profile": manifest.get("chrome_profile", "Default"),
                                "backup_date": manifest.get("backup_date", date_str),
                                "file_count": manifest.get("file_count", file_count),
                                "size_bytes": file_size,
                                "size_formatted": format_bytes(file_size),
                                "is_encrypted": encrypted or manifest.get("is_encrypted", False),
                                "is_locked": manifest.get("is_locked", False),
                                "is_incremental": manifest.get("is_incremental", False),
                                "format": "crxbackup" if f.endswith(".crxbackup") else "zip",
                                "compression_level": manifest.get("compression_level", 6),
                                "integrity_status": "Válido"
                            })
                    except Exception:
                        continue
        return backups

    def handle_list_backups(self, payload: dict) -> dict:
        primary_dir = self.settings.get("primary_backup_dir") or get_default_backup_dir()
        backups = self._scan_backups_in_dir(primary_dir)
        
        # Sort newest first
        backups.sort(key=lambda x: x.get("backup_date", ""), reverse=True)
        return {
            "success": True,
            "backups": backups,
            "total_count": len(backups),
            "directory": primary_dir
        }

    def handle_validate_backup(self, payload: dict) -> dict:
        backup_path = payload.get("backup_path")
        password = payload.get("password")
        if not backup_path or not os.path.exists(backup_path):
            return create_error_response("BK-0001", "validation", backup_path or "", "Ficheiro de backup não existe.")

        res = validate_archive_integrity(backup_path, password)
        # Log and record
        fname = os.path.basename(backup_path)
        record_history_entry(
            "Validation",
            fname,
            "",
            "",
            "",
            "Sucesso" if res.get("valid") else "Falha",
            res.get("error", "") if not res.get("valid") else ""
        )
        return res

    def handle_restore_extension(self, payload: dict) -> dict:
        backup_path = payload.get("backup_path")
        target_profile = payload.get("target_profile", "Default")
        restore_mode = payload.get("restore_mode", "direct_profile")
        custom_export_dir = payload.get("custom_export_dir")
        password = payload.get("password")
        force_running = payload.get("force_even_if_chrome_running", True)

        res = self.restore_engine.restore_extension(
            backup_file=backup_path,
            target_profile_id=target_profile,
            restore_mode=restore_mode,
            custom_export_dir=custom_export_dir,
            password=password,
            force_even_if_chrome_running=force_running
        )

        ext_name = res.get("extension_name", os.path.basename(backup_path))
        ext_id = res.get("extension_id", "")
        ver = res.get("version", "")
        if res.get("success"):
            record_history_entry("Restore", ext_name, ext_id, target_profile, ver, "Sucesso")
        else:
            record_history_entry("Restore", ext_name, ext_id, target_profile, ver, "Falha", res.get("error", {}).get("description", ""))

        return res

    def handle_revert_rollback(self, payload: dict) -> dict:
        rollback_id = payload.get("rollback_id")
        dest_path = payload.get("destination_path")
        res = self.restore_engine.revert_rollback(rollback_id, dest_path)
        if res.get("success"):
            record_history_entry("Rollback", rollback_id, "", "", "", "Sucesso")
        else:
            record_history_entry("Rollback", rollback_id, "", "", "", "Falha", res.get("error", {}).get("description", ""))
        return res

    def handle_compare_backups(self, payload: dict) -> dict:
        item_a = payload.get("item_a_path")
        item_b = payload.get("item_b_path")
        pass_a = payload.get("password_a")
        pass_b = payload.get("password_b")
        return compare_two_versions(item_a, item_b, pass_a, pass_b)

    def handle_delete_backup(self, payload: dict) -> dict:
        backup_path = payload.get("backup_path")
        if not backup_path or not os.path.exists(backup_path):
            return {"success": False, "message": "Ficheiro de backup não encontrado."}

        # Check if locked
        try:
            with zipfile.ZipFile(backup_path, "r") as z:
                if "manifest.json" in z.namelist():
                    with z.open("manifest.json") as mf:
                        m = json.load(mf)
                        if m.get("is_locked", False):
                            return {"success": False, "message": "Este backup está bloqueado contra eliminação. Desbloqueie-o primeiro."}
        except Exception:
            pass

        try:
            os.remove(backup_path)
            fname = os.path.basename(backup_path)
            record_history_entry("Delete", fname, "", "", "", "Sucesso")
            return {"success": True, "message": f"Backup {fname} eliminado com sucesso."}
        except Exception as e:
            return {"success": False, "message": f"Erro ao eliminar backup: {e}"}

    def handle_scan_custom_folder(self, payload: dict) -> dict:
        target_dir = payload.get("folder_path")
        if not target_dir or not os.path.exists(target_dir):
            return {"success": False, "message": "Diretório inválido ou inacessível."}

        backups = self._scan_backups_in_dir(target_dir)
        return {
            "success": True,
            "folder": target_dir,
            "backups": backups,
            "count": len(backups)
        }

    def handle_check_disk_space(self, payload: dict) -> dict:
        path = payload.get("path") or self.settings.get("primary_backup_dir") or get_default_backup_dir()
        return {
            "success": True,
            "disk": get_disk_free_space(path)
        }

    def handle_get_history(self, payload: dict) -> dict:
        return {
            "success": True,
            "history": load_history()
        }

    def handle_get_logs(self, payload: dict) -> dict:
        return {
            "success": True,
            "logs": logger.get_logs(500)
        }

    def handle_export_logs(self, payload: dict) -> dict:
        target = payload.get("target_file") or os.path.join(
            os.path.expanduser("~"), "Documents", "ChromeExtBackup_Diagnostics.txt"
        )
        ok = logger.export_logs(target)
        return {
            "success": ok,
            "target_file": target,
            "message": f"Logs exportados com sucesso para: {target}" if ok else "Falha ao exportar logs."
        }

    def handle_get_settings(self, payload: dict) -> dict:
        return {
            "success": True,
            "settings": self.settings
        }

    def handle_save_settings(self, payload: dict) -> dict:
        new_settings = payload.get("settings", {})
        self.settings.update(new_settings)
        ok = save_app_settings(self.settings)
        self.reload_config()
        return {
            "success": ok,
            "settings": self.settings,
            "message": "Definições guardadas com sucesso!"
        }

    def handle_get_license(self, payload: dict) -> dict:
        return {
            "success": True,
            "license": license_mgr.get_info()
        }

    def handle_activate_license(self, payload: dict) -> dict:
        key = payload.get("license_key", "")
        name = payload.get("registered_to", "Utilizador Registado")
        res = license_mgr.activate(key, name)
        return res

    def handle_deactivate_license(self, payload: dict) -> dict:
        return license_mgr.deactivate()

    def handle_get_schedule(self, payload: dict) -> dict:
        return {
            "success": True,
            "schedule": get_schedule_config()
        }

    def handle_save_schedule(self, payload: dict) -> dict:
        cfg = payload.get("schedule", {})
        # If enabled, register with Windows Task Scheduler
        res = register_windows_task(cfg)
        return res

    def handle_check_for_changes(self, payload: dict) -> dict:
        """Compares currently installed extensions against recorded backup manifests to detect changes."""
        profiles = self.detector.detect_profiles()
        changes = []
        primary_dir = self.settings.get("primary_backup_dir") or get_default_backup_dir()
        existing_backups = self._scan_backups_in_dir(primary_dir)

        for prof in profiles:
            pid = prof["profile_id"]
            exts = self.detector.get_installed_extensions(pid)
            for ext in exts:
                eid = ext["extension_id"]
                matching = [b for b in existing_backups if b.get("extension_id") == eid]
                if matching:
                    matching.sort(key=lambda x: x.get("backup_date", ""), reverse=True)
                    latest = matching[0]
                    if ext["version"] != latest.get("version"):
                        changes.append({
                            "extension_id": eid,
                            "name": ext["name"],
                            "profile_id": pid,
                            "previous_version": latest.get("version"),
                            "current_version": ext["version"],
                            "message": f"Nova versão detetada: {ext['name']} (v{latest.get('version')} -> v{ext['version']})"
                        })

        return {
            "success": True,
            "changes_detected": len(changes) > 0,
            "changes": changes
        }

    def handle_open_folder(self, payload: dict) -> dict:
        folder_path = payload.get("folder_path")
        if not folder_path or not os.path.exists(folder_path):
            return {"success": False, "error": f"Pasta não encontrada: {folder_path}"}
        try:
            import subprocess
            if hasattr(os, "startfile"):
                os.startfile(folder_path)
            else:
                subprocess.Popen(["explorer.exe", folder_path])
            return {"success": True}
        except Exception as e:
            logger.error(f"Erro ao abrir pasta: {e}", "SYSTEM")
            return {"success": False, "error": str(e)}

    def handle_open_chrome_extensions(self, payload: dict) -> dict:
        try:
            import subprocess
            subprocess.Popen(["cmd.exe", "/c", "start", "chrome.exe", "chrome://extensions"])
            return {"success": True}
        except Exception as e:
            logger.error(f"Erro ao abrir chrome://extensions: {e}", "SYSTEM")
            return {"success": False, "error": str(e)}

    def handle_open_file_dialog(self, payload: dict) -> dict:
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes("-topmost", 1)
            file_path = filedialog.askopenfilename(
                title="Selecionar Ficheiro de Backup (.crxbackup ou .zip)",
                filetypes=[
                    ("Arquivos de Backup e ZIP (*.crxbackup; *.zip)", "*.crxbackup;*.zip"),
                    ("Chrome Extension Backup (*.crxbackup)", "*.crxbackup"),
                    ("Ficheiros ZIP da Extensão (*.zip)", "*.zip"),
                    ("Todos os Ficheiros (*.*)", "*.*")
                ]
            )
            root.destroy()
            if not file_path:
                return {"success": False, "cancelled": True}

            file_path = os.path.normpath(file_path)
            return {"success": True, "file_path": file_path}
        except Exception as e:
            logger.error(f"Erro ao abrir seletor de ficheiros: {e}", "SYSTEM")
            return {"success": False, "error": str(e)}

    def handle_inspect_backup_file(self, payload: dict) -> dict:
        backup_path = payload.get("backup_path")
        if not backup_path or not os.path.exists(backup_path):
            return {"success": False, "error": f"Ficheiro de backup não encontrado: {backup_path}"}
        password = payload.get("password")
        try:
            engine = RestoreEngine()
            info = engine.inspect_backup_archive(backup_path, password)
            return {"success": True, "info": info}
        except Exception as e:
            logger.error(f"Erro ao inspecionar backup: {e}", "SYSTEM")
            return {"success": False, "error": str(e)}

    def handle_import_backup_file(self, payload: dict) -> dict:
        filename = payload.get("filename")
        base64_data = payload.get("base64_data")
        if not filename or not base64_data:
            return {"success": False, "error": "Nome do ficheiro ou dados base64 ausentes."}
        try:
            import base64
            backup_dir = get_default_backup_dir()
            target_path = os.path.join(backup_dir, filename)
            os.makedirs(backup_dir, exist_ok=True)
            raw_bytes = base64.b64decode(base64_data)
            with open(target_path, "wb") as f:
                f.write(raw_bytes)
            engine = RestoreEngine()
            info = engine.inspect_backup_archive(target_path)
            return {"success": True, "file_path": target_path, "info": info}
        except Exception as e:
            logger.error(f"Erro ao importar backup: {e}", "SYSTEM")
            return {"success": False, "error": str(e)}

    def handle_launch_chrome_with_extension(self, payload: dict) -> dict:
        folder_path = payload.get("folder_path")
        if not folder_path or not os.path.exists(folder_path):
            return {"success": False, "error": f"Pasta não encontrada: {folder_path}"}
        try:
            import subprocess
            cmd = f'start chrome.exe --load-extension="{folder_path}" chrome://extensions'
            subprocess.Popen(["cmd.exe", "/c", cmd])
            return {"success": True}
        except Exception as e:
            logger.error(f"Erro ao iniciar Chrome com extensão: {e}", "SYSTEM")
            return {"success": False, "error": str(e)}

    def dispatch(self, action: str, payload: dict) -> dict:
        action_map = {
            "ping": self.handle_ping,
            "get_system_info": self.handle_get_system_info,
            "get_profiles": self.handle_get_profiles,
            "get_extensions": self.handle_get_extensions,
            "check_chrome_running": self.handle_check_chrome_running,
            "close_chrome": self.handle_close_chrome,
            "backup_extension": self.handle_backup_extension,
            "list_backups": self.handle_list_backups,
            "validate_backup": self.handle_validate_backup,
            "restore_extension": self.handle_restore_extension,
            "revert_rollback": self.handle_revert_rollback,
            "compare_backups": self.handle_compare_backups,
            "delete_backup": self.handle_delete_backup,
            "scan_custom_folder": self.handle_scan_custom_folder,
            "check_disk_space": self.handle_check_disk_space,
            "get_history": self.handle_get_history,
            "get_logs": self.handle_get_logs,
            "export_logs": self.handle_export_logs,
            "get_settings": self.handle_get_settings,
            "save_settings": self.handle_save_settings,
            "get_license": self.handle_get_license,
            "activate_license": self.handle_activate_license,
            "deactivate_license": self.handle_deactivate_license,
            "get_schedule": self.handle_get_schedule,
            "save_schedule": self.handle_save_schedule,
            "check_for_changes": self.handle_check_for_changes,
            "open_folder": self.handle_open_folder,
            "open_chrome_extensions": self.handle_open_chrome_extensions,
            "open_file_dialog": self.handle_open_file_dialog,
            "inspect_backup_file": self.handle_inspect_backup_file,
            "import_backup_file": self.handle_import_backup_file,
            "launch_chrome_with_extension": self.handle_launch_chrome_with_extension
        }

        handler = action_map.get(action)
        if not handler:
            return create_error_response("NT-0001", action, "", f"Comando '{action}' não suportado pelo Native Host.")

        try:
            return handler(payload)
        except Exception as e:
            logger.error(f"Exceção não tratada no handler '{action}': {e}", "DISPATCH")
            return {
                "success": False,
                "error": {
                    "code": "NT-0000",
                    "title": "Erro Interno no Native Host",
                    "description": str(e),
                    "operation": action,
                    "solution": "Consulte os logs em Logs/ para detalhes de diagnóstico."
                }
            }


def read_native_message():
    """Reads 32-bit unsigned little-endian length prefix followed by JSON payload."""
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) == 0:
        return None
    message_length = struct.unpack("<I", raw_length)[0]
    message_bytes = sys.stdin.buffer.read(message_length)
    return json.loads(message_bytes.decode("utf-8"))


def send_native_message(message: dict):
    """Sends JSON message prefixed with 32-bit unsigned little-endian length."""
    encoded_bytes = json.dumps(message, ensure_ascii=False).encode("utf-8")
    length_prefix = struct.pack("<I", len(encoded_bytes))
    sys.stdout.buffer.write(length_prefix)
    sys.stdout.buffer.write(encoded_bytes)
    sys.stdout.buffer.flush()


def run_scheduled_job():
    """Headless background runner executed by Windows Task Scheduler."""
    logger.info("Executando trabalho agendado de backup em segundo plano...", "SCHEDULER")
    cfg = get_schedule_config()
    handler = HostCommandHandler()
    profiles = cfg.get("profiles", ["Default"])
    if cfg.get("backup_all_profiles", True):
        profiles = [p["profile_id"] for p in handler.detector.detect_profiles()]

    backed_up = 0
    errors = 0
    for pid in profiles:
        exts = handler.detector.get_installed_extensions(pid)
        for ext in exts:
            res = handler.handle_backup_extension({
                "extension_id": ext["extension_id"],
                "extension_name": ext["name"],
                "version": ext["version"],
                "source_dir": ext["local_path"],
                "profile_id": pid,
                "is_incremental": cfg.get("is_incremental", True),
                "compression_level": cfg.get("compression_level", 6)
            })
            if res.get("success"):
                backed_up += 1
            else:
                errors += 1

    cfg["last_run"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cfg["last_status"] = f"Concluído: {backed_up} backups criados, {errors} erros."
    save_schedule_config(cfg)
    logger.info(f"Trabalho agendado concluído: {cfg['last_status']}", "SCHEDULER")


def main():
    if "--run-scheduled" in sys.argv:
        run_scheduled_job()
        sys.exit(0)

    # Set stdout to binary mode for Windows
    if sys.platform == "win32":
        import msvcrt
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

    handler = HostCommandHandler()
    logger.info("Host Native Messaging do ChromeExtensionBackupPro iniciado com sucesso.", "STARTUP")

    while True:
        try:
            msg = read_native_message()
            if msg is None:
                break

            action = msg.get("action", "ping")
            payload = msg.get("payload", {})
            response = handler.dispatch(action, payload)
            
            # Echo correlation ID if provided
            if "requestId" in msg:
                response["requestId"] = msg["requestId"]

            send_native_message(response)
        except Exception as e:
            logger.error(f"Erro no ciclo principal de mensagens: {e}", "MAIN")
            send_native_message({
                "success": False,
                "error": {
                    "code": "NT-9999",
                    "title": "Erro de Protocolo",
                    "description": str(e)
                }
            })


if __name__ == "__main__":
    main()
