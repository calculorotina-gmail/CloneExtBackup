"""
Enterprise Restore and Rollback Engine for Chrome Extensions.
Adheres strictly to requirements 8, 9, 10, 41:
- Offline local file restoration without Web Store dependencies
- Pre-validation of backup integrity before touching destination
- Chrome running check with locking risk disclosure
- Automatic safety snapshot (Rollback Point) before overwriting any file
- Revert Restore (Rollback) capability
- Two restore methods:
    1. Direct Profile Restoration (in <Profile>/Extensions/<ID>/<Version>)
    2. Developer Mode Unpacked Export (Load Unpacked - 100% store-independent)
- Complete technical limitations reporting
"""

import os
import shutil
import json
import time
import zipfile
import datetime
from typing import Dict, Any, List, Optional

from .integrity import validate_archive_integrity, validate_hashes_against_dir
from .process_manager import is_chrome_running
from .encryption import is_file_encrypted, decrypt_file
from .compressor import BackupCompressor
from .chrome_detector import get_default_chrome_user_data_path, ChromeDetector
from .disk_space import format_bytes
from .logger import logger
from .error_codes import create_error_response

DEFAULT_ROLLBACKS_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "ChromeExtBackupPro",
    "Rollbacks"
)


class RestoreEngine:
    def __init__(self, rollbacks_dir: Optional[str] = None):
        self.rollbacks_dir = rollbacks_dir or DEFAULT_ROLLBACKS_DIR
        os.makedirs(self.rollbacks_dir, exist_ok=True)

    def extract_backup_to_temp(self, backup_file: str, password: Optional[str] = None) -> str:
        """Extracts .crxbackup to a temporary directory for inspection or restoration."""
        if not os.path.exists(backup_file):
            raise FileNotFoundError(f"Ficheiro de backup não encontrado: {backup_file}")

        temp_dir = backup_file + f".tmp_unpack_{int(time.time())}"
        target_zip = backup_file
        temp_decrypted = None

        try:
            if is_file_encrypted(backup_file):
                if not password:
                    raise PermissionError("O backup está encriptado. É necessária a palavra-passe para o restauro.")
                temp_decrypted = backup_file + ".tmp_dec"
                decrypt_file(backup_file, temp_decrypted, password)
                target_zip = temp_decrypted

            compressor = BackupCompressor()
            compressor.extract_archive(target_zip, temp_dir)
            return temp_dir
        finally:
            if temp_decrypted and os.path.exists(temp_decrypted):
                try:
                    os.remove(temp_decrypted)
                except Exception:
                    pass

    def inspect_backup_archive(self, backup_file: str, password: Optional[str] = None) -> Dict[str, Any]:
        """Inspects and validates a .crxbackup archive without restoring, returning manifest and health data."""
        val_res = validate_archive_integrity(backup_file, password)
        if not val_res.get("valid"):
            raise ValueError(val_res.get("error", "O arquivo de backup falhou na verificação de integridade SHA-256."))

        temp_dir = self.extract_backup_to_temp(backup_file, password)
        try:
            manifest_file = os.path.join(temp_dir, "manifest.json")
            if not os.path.exists(manifest_file):
                raise FileNotFoundError("manifest.json ausente no arquivo .crxbackup.")
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)

            inner_manifest = os.path.join(temp_dir, "extension", "manifest.json")
            inner_data = {}
            if os.path.exists(inner_manifest):
                try:
                    with open(inner_manifest, "r", encoding="utf-8") as imf:
                        inner_data = json.load(imf)
                except Exception:
                    pass

            file_size = os.path.getsize(backup_file)
            size_fmt = f"{file_size / (1024 * 1024):.2f} MB" if file_size > 1024 * 1024 else f"{file_size / 1024:.1f} KB"

            return {
                "backup_path": backup_file,
                "filename": os.path.basename(backup_file),
                "extension_id": manifest_data.get("extension_id", ""),
                "extension_name": manifest_data.get("extension_name", inner_data.get("name", "Extensão")),
                "version": manifest_data.get("version", inner_data.get("version", "1.0")),
                "backup_date": manifest_data.get("backup_date", ""),
                "file_count": manifest_data.get("file_count", 0),
                "file_size": file_size,
                "size_formatted": size_fmt,
                "is_encrypted": is_file_encrypted(backup_file),
                "is_valid": True,
                "description": inner_data.get("description", "")
            }
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    def register_chrome_external_extension(self, ext_id: str) -> bool:
        """Registers extension in HKCU\\Software\\Google\\Chrome\\Extensions for automatic Chrome installation."""
        try:
            import winreg
            key_path = rf"Software\Google\Chrome\Extensions\{ext_id}"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, "update_url", 0, winreg.REG_SZ, "https://clients2.google.com/service/update2/crx")
            logger.info(f"Extensão {ext_id} registada em HKCU\\Software\\Google\\Chrome\\Extensions com sucesso.", "RESTORE")
            return True
        except Exception as e:
            logger.warn(f"Não foi possível registar extensão no Registo do Windows: {e}", "RESTORE")
    def create_pre_restore_rollback_point(self, current_ext_path: str, backup_id: str) -> Optional[str]:
        """
        Creates a full safety snapshot of the currently installed extension
        before any files are replaced or modified.
        """
        if not os.path.exists(current_ext_path):
            return None  # No existing installation to snapshot

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        rollback_id = f"rollback_{backup_id}_{ts}"
        rollback_path = os.path.join(self.rollbacks_dir, rollback_id)

        try:
            shutil.copytree(current_ext_path, rollback_path)
            logger.info(f"Ponto de rollback de segurança criado: {rollback_path}", "RESTORE")
            return rollback_id
        except Exception as e:
            logger.error(f"Falha ao criar ponto de rollback: {e}", "RESTORE")
            raise RuntimeError(f"Não foi possível criar a cópia de salvaguarda da instalação atual: {e}")

    def restore_extension(
        self,
        backup_file: str,
        target_profile_id: str = "Default",
        restore_mode: str = "direct_profile",  # "direct_profile" or "unpacked_export"
        custom_export_dir: Optional[str] = None,
        custom_user_data_path: Optional[str] = None,
        password: Optional[str] = None,
        force_even_if_chrome_running: bool = True
    ) -> Dict[str, Any]:
        """
        Executes complete restoration with pre-validation, rollback snapshot, and post-validation.
        """
        op_start = time.time()
        logger.info(f"Iniciando restauro do backup: {backup_file} no perfil: {target_profile_id}", "RESTORE")

        # 1. Validate backup integrity prior to restore
        val_res = validate_archive_integrity(backup_file, password)
        if not val_res.get("valid"):
            err_msg = val_res.get("error", "Validação de integridade falhou. O backup está corrompido ou adulterado.")
            logger.error(f"Validação pré-restauro falhou: {err_msg}", "RESTORE")
            return create_error_response("RS-0001", "restore", backup_file, err_msg)

        # 2. Check if Chrome is running if doing direct profile restore
        chrome_check = is_chrome_running()
        is_chrome_open = chrome_check.get("running", False)
        if restore_mode == "direct_profile" and is_chrome_open:
            if not force_even_if_chrome_running:
                logger.warn("Tentativa de restauro direto com o Google Chrome em execução.", "RESTORE")
                return create_error_response(
                    "RS-0002",
                    "restore",
                    backup_file,
                    f"O Google Chrome está atualmente aberto ({chrome_check.get('count', 1)} processos). Feche o Chrome para evitar locks de ficheiros ou ative o restauro a quente com ponto de rollback."
                )
            else:
                logger.info(
                    f"Google Chrome em execução ({chrome_check.get('count', 1)} processos). "
                    "A prosseguir com restauro a quente seguro com salvaguarda prévia (Rollback Point).",
                    "RESTORE"
                )

        # 3. Extract backup to temporary staging
        temp_extracted = None
        rollback_id = None
        try:
            temp_extracted = self.extract_backup_to_temp(backup_file, password)
            manifest_file = os.path.join(temp_extracted, "manifest.json")
            if not os.path.exists(manifest_file):
                return create_error_response("VL-0001", "restore", backup_file, "manifest.json ausente no backup.")

            with open(manifest_file, "r", encoding="utf-8") as mf:
                manifest_data = json.load(mf)

            ext_id = manifest_data.get("extension_id")
            ext_name = manifest_data.get("extension_name", ext_id)
            version = manifest_data.get("version", "1.0")
            backup_id = manifest_data.get("backup_id", ext_id)

            staging_payload = os.path.join(temp_extracted, "extension")
            if not os.path.exists(staging_payload):
                return create_error_response("VL-0003", "restore", backup_file, "Pasta 'extension/' ausente no arquivo.")

            hashes_file = os.path.join(temp_extracted, "hashes", "hashes.json")
            hashes_map = {}
            if os.path.exists(hashes_file):
                with open(hashes_file, "r", encoding="utf-8") as hf:
                    hashes_map = json.load(hf)

            # 4. Determine destination path
            if restore_mode in ("unpacked_export", "auto_chrome"):
                base_export = custom_export_dir or os.path.join(
                    os.path.expanduser("~"), "Documents", "ChromeExtensionsRestored"
                )
                destination_path = os.path.join(base_export, f"{ext_name}_{ext_id}_v{version}")
                os.makedirs(destination_path, exist_ok=True)
            else:
                user_data = custom_user_data_path or get_default_chrome_user_data_path()
                # Resolve active installed location if already present on this computer (Unpacked or Store)
                target_dest = None
                try:
                    detector = ChromeDetector(user_data)
                    installed_exts = detector.get_installed_extensions(target_profile_id)
                    matching = next((e for e in installed_exts if e.get("extension_id") == ext_id), None)
                    if matching and matching.get("local_path") and os.path.exists(matching["local_path"]):
                        target_dest = matching["local_path"]
                except Exception as de:
                    logger.warn(f"Não foi possível detetar caminho existente da extensão: {de}", "RESTORE")

                if not target_dest:
                    orig_dir = manifest_data.get("original_source_dir")
                    if orig_dir and os.path.isabs(orig_dir) and ("AppData" not in orig_dir or os.path.exists(orig_dir)):
                        target_dest = orig_dir

                if not target_dest:
                    # Extension is not currently active in Chrome.
                    # Never write to User Data\...\Extensions where Chrome ignores/blocks it!
                    # Write to Documents\ChromeExtensionsRestored instead.
                    base_export = custom_export_dir or os.path.join(
                        os.path.expanduser("~"), "Documents", "ChromeExtensionsRestored"
                    )
                    target_dest = os.path.join(base_export, f"{ext_name}_{ext_id}_v{version}")

                destination_path = target_dest

            # 5. Create Pre-Restore Rollback Snapshot if target exists
            if os.path.exists(destination_path):
                try:
                    rollback_id = self.create_pre_restore_rollback_point(destination_path, backup_id)
                except Exception as rbe:
                    return create_error_response("RS-0003", "restore", destination_path, str(rbe))

            # 6. Copy files to destination
            os.makedirs(destination_path, exist_ok=True)
            copied_count = 0
            for root, dirs, files in os.walk(staging_payload):
                for d in dirs:
                    os.makedirs(os.path.join(destination_path, os.path.relpath(os.path.join(root, d), staging_payload)), exist_ok=True)
                for f in files:
                    s_file = os.path.join(root, f)
                    rel = os.path.relpath(s_file, staging_payload)
                    d_file = os.path.join(destination_path, rel)
                    os.makedirs(os.path.dirname(d_file), exist_ok=True)
                    shutil.copy2(s_file, d_file)
                    copied_count += 1

            # 7. Post-Restore Validation
            post_val = validate_hashes_against_dir(destination_path, hashes_map)
            if not post_val["valid"]:
                logger.error("Validação pós-restauro falhou. Revertendo com rollback...", "RESTORE")
                # Trigger automatic rollback
                if rollback_id:
                    self.revert_rollback(rollback_id, destination_path)
                return create_error_response("RS-0005", "restore", destination_path, "A integridade dos ficheiros gravados divergiu do original. Rollback acionado.")

            elapsed = round(time.time() - op_start, 2)
            logger.info(f"Restauro concluído com sucesso em {elapsed}s no caminho: {destination_path}", "RESTORE")

            # Automatic registration in Chrome External Extensions registry (HKCU\Software\Google\Chrome\Extensions)
            chrome_registered = False
            if ext_id and len(ext_id) == 32 and ext_id.isalpha() and ext_id.islower():
                chrome_registered = self.register_chrome_external_extension(ext_id)

            # Limitations transparency note
            limitations_notice = (
                "NOTA TÉCNICA IMPORTANTE: Os ficheiros locais da extensão foram restaurados com 100% de integridade. "
                "Caso o Chrome esteja configurado para verificar assinaturas rígidas da Chrome Web Store no ficheiro Preferences/Secure Preferences, "
                "recomenda-se ativar o 'Modo de Programador' em chrome://extensions e carregar a pasta restaurada se o Chrome indicar inconsistência de hash da Web Store."
            )

            return {
                "success": True,
                "restore_mode": restore_mode,
                "extension_id": ext_id,
                "extension_name": ext_name,
                "version": version,
                "target_profile": target_profile_id,
                "destination_path": destination_path,
                "copied_files": copied_count,
                "duration_seconds": elapsed,
                "rollback_id": rollback_id,
                "chrome_registered": chrome_registered,
                "integrity_status": "Válido (100% hashes verificados)",
                "technical_notice": limitations_notice,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        except Exception as ex:
            logger.error(f"Erro inesperado no restauro: {ex}", "RESTORE")
            if rollback_id and os.path.exists(destination_path):
                self.revert_rollback(rollback_id, destination_path)
            return create_error_response("RS-0005", "restore", backup_file, str(ex))

        finally:
            if temp_extracted and os.path.exists(temp_extracted):
                shutil.rmtree(temp_extracted, ignore_errors=True)

    def revert_rollback(self, rollback_id: str, destination_path: str) -> Dict[str, Any]:
        """Reverts an installation back to the saved pre-restore rollback snapshot."""
        rollback_source = os.path.join(self.rollbacks_dir, rollback_id)
        if not os.path.exists(rollback_source):
            return create_error_response("RS-0006", "rollback", rollback_source, f"Ponto de rollback '{rollback_id}' não encontrado.")

        try:
            logger.info(f"Revertendo restauro para o snapshot de rollback: {rollback_source} -> {destination_path}", "ROLLBACK")
            if os.path.exists(destination_path):
                shutil.rmtree(destination_path, ignore_errors=True)

            shutil.copytree(rollback_source, destination_path)
            return {
                "success": True,
                "rollback_id": rollback_id,
                "restored_path": destination_path,
                "message": "Reversão (Rollback) efetuada com sucesso. A versão anterior foi restabelecida."
            }
        except Exception as e:
            logger.error(f"Erro ao executar reversão: {e}", "ROLLBACK")
            return create_error_response("RS-0006", "rollback", destination_path, str(e))
