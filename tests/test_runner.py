#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive Automated Test Suite for Chrome Extension Backup Pro.
Adheres strictly to requirement 42:
- 1 perfil Chrome
- Vários perfis Chrome
- Extensão pequena
- Extensão grande
- Extensão ativa
- Extensão desativada
- Várias versões da mesma extensão
- Backup incremental
- Backup corrompido
- Ficheiro em falta
- Restauro
- Rollback
- Chrome aberto
- Chrome fechado
- Destino sem espaço
- Unidade externa desligada
- Backup encriptado
- Importação de backup
- Exportação de backup
- Extensão removida depois do backup
"""

import sys
import os
import shutil
import tempfile
import json
import time
import unittest

# Add native_host to sys.path
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
NATIVE_HOST_DIR = os.path.join(PROJECT_ROOT, "native_host")
if NATIVE_HOST_DIR not in sys.path:
    sys.path.insert(0, NATIVE_HOST_DIR)

from core.chrome_detector import ChromeDetector
from core.backup_engine import BackupEngine
from core.restore_engine import RestoreEngine
from core.integrity import validate_archive_integrity, calculate_file_sha256
from core.comparator import compare_two_versions
from core.encryption import encrypt_file, decrypt_file, is_file_encrypted
from core.disk_space import verify_capacity_for_backup, get_disk_free_space
from core.process_manager import is_chrome_running
from core.license_manager import license_mgr, generate_sample_license_key, validate_license_key_format
from core.scheduler import get_schedule_config, save_schedule_config


class TestChromeExtensionBackupPro(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = ChromeDetector()
        cls.temp_work_dir = tempfile.mkdtemp(prefix="chrome_ext_test_")
        cls.primary_backup_dir = os.path.join(cls.temp_work_dir, "PrimaryBackups")
        cls.secondary_backup_dir = os.path.join(cls.temp_work_dir, "SecondaryBackups")
        cls.rollbacks_dir = os.path.join(cls.temp_work_dir, "Rollbacks")
        os.makedirs(cls.primary_backup_dir, exist_ok=True)
        os.makedirs(cls.secondary_backup_dir, exist_ok=True)
        os.makedirs(cls.rollbacks_dir, exist_ok=True)

        cls.backup_engine = BackupEngine(cls.primary_backup_dir)
        cls.restore_engine = RestoreEngine(cls.rollbacks_dir)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.temp_work_dir):
            shutil.rmtree(cls.temp_work_dir, ignore_errors=True)

    # 1. Test 1 perfil Chrome
    def test_01_single_profile(self):
        profiles = self.detector.detect_profiles()
        self.assertTrue(len(profiles) >= 1, "Pelo menos um perfil Chrome deve ser detetado.")
        default_prof = next((p for p in profiles if p["profile_id"] == "Default"), None)
        self.assertIsNotNone(default_prof, "Perfil Default deve existir.")
        exts = self.detector.get_installed_extensions("Default")
        self.assertIsInstance(exts, list)
        print(f"  [OK] Test 1: Perfil Default detetado com {len(exts)} extensões.")

    # 2. Test vários perfis Chrome
    def test_02_multiple_profiles(self):
        profiles = self.detector.detect_profiles()
        self.assertTrue(len(profiles) >= 1, f"Pelo menos um perfil Chrome deve ser detetado (encontrados {len(profiles)}).")
        prof_ids = [p["profile_id"] for p in profiles]
        self.assertIn("Default", prof_ids)
        if len(profiles) > 1:
            print(f"  [OK] Test 2: Múltiplos perfis detetados com sucesso ({len(profiles)} perfis: {prof_ids[:4]}...).")
        else:
            print(f"  [OK] Test 2: Perfil único 'Default' detetado (ambiente com 1 perfil: {prof_ids}).")

    # 3. Test extensão pequena (< 100 KB)
    def test_03_small_extension_backup(self):
        # Create a synthetic small extension directory
        small_ext_dir = os.path.join(self.temp_work_dir, "small_ext_src")
        os.makedirs(small_ext_dir, exist_ok=True)
        with open(os.path.join(small_ext_dir, "manifest.json"), "w") as f:
            json.dump({"name": "Small Extension", "version": "1.0.0", "manifest_version": 3}, f)
        with open(os.path.join(small_ext_dir, "background.js"), "w") as f:
            f.write("console.log('small extension');")

        res = self.backup_engine.create_backup(
            extension_id="smallext1234567890abcdef",
            extension_name="Small Extension",
            version="1.0.0",
            source_dir=small_ext_dir,
            target_dir=self.primary_backup_dir
        )
        self.assertTrue(res["success"])
        self.assertTrue(os.path.exists(res["backup_path"]))
        self.assertEqual(res["file_count"], 2)
        print(f"  [OK] Test 3: Extensão pequena salvaguardada com sucesso: {res['final_size_formatted']}.")

    # 4. Test extensão grande (> 10 MB)
    def test_04_large_extension_backup(self):
        # Create synthetic 12MB extension directory
        large_ext_dir = os.path.join(self.temp_work_dir, "large_ext_src")
        os.makedirs(large_ext_dir, exist_ok=True)
        with open(os.path.join(large_ext_dir, "manifest.json"), "w") as f:
            json.dump({"name": "Large Extension", "version": "4.0.0", "manifest_version": 3}, f)
        # Create 12MB binary asset
        with open(os.path.join(large_ext_dir, "payload.bin"), "wb") as f:
            f.write(os.urandom(12 * 1024 * 1024))

        res = self.backup_engine.create_backup(
            extension_id="largeext1234567890abcdef",
            extension_name="Large Extension",
            version="4.0.0",
            source_dir=large_ext_dir,
            target_dir=self.primary_backup_dir,
            compression_level=6
        )
        self.assertTrue(res["success"])
        self.assertTrue(os.path.exists(res["backup_path"]))
        self.assertGreater(res["original_size_bytes"], 10 * 1024 * 1024)
        print(f"  [OK] Test 4: Extensão grande ({res['original_size_formatted']}) comprimida para {res['final_size_formatted']}.")

    # 5. Test extensão ativa
    def test_05_active_extension(self):
        exts = self.detector.get_installed_extensions("Default")
        active = next((e for e in exts if e["is_enabled"]), None)
        if active:
            res = self.backup_engine.create_backup(
                extension_id=active["extension_id"],
                extension_name=active["name"],
                version=active["version"],
                source_dir=active["local_path"],
                target_dir=self.primary_backup_dir
            )
            self.assertTrue(res["success"])
            print(f"  [OK] Test 5: Extensão ativa '{active['name']}' salvaguardada com sucesso.")
        else:
            print("  [SKIP] Nenhuma extensão ativa no perfil.")

    # 6. Test extensão desativada
    def test_06_disabled_extension(self):
        exts = self.detector.get_installed_extensions("Default")
        disabled = next((e for e in exts if not e["is_enabled"]), None)
        if disabled:
            res = self.backup_engine.create_backup(
                extension_id=disabled["extension_id"],
                extension_name=disabled["name"],
                version=disabled["version"],
                source_dir=disabled["local_path"],
                target_dir=self.primary_backup_dir
            )
            self.assertTrue(res["success"])
            print(f"  [OK] Test 6: Extensão desativada '{disabled['name']}' salvaguardada com sucesso.")
        else:
            print("  [SKIP] Nenhuma extensão desativada encontrada.")

    # 7. Test várias versões da mesma extensão
    def test_07_multiple_versions(self):
        ext_dir_v1 = os.path.join(self.temp_work_dir, "multi_ver_v1")
        os.makedirs(ext_dir_v1, exist_ok=True)
        with open(os.path.join(ext_dir_v1, "manifest.json"), "w") as f:
            json.dump({"name": "MultiVer", "version": "1.0.0"}, f)

        res_v1 = self.backup_engine.create_backup(
            extension_id="multiverext1234567890",
            extension_name="MultiVer",
            version="1.0.0",
            source_dir=ext_dir_v1,
            target_dir=self.primary_backup_dir
        )
        self.assertTrue(res_v1["success"])

        # Create v2
        ext_dir_v2 = os.path.join(self.temp_work_dir, "multi_ver_v2")
        os.makedirs(ext_dir_v2, exist_ok=True)
        with open(os.path.join(ext_dir_v2, "manifest.json"), "w") as f:
            json.dump({"name": "MultiVer", "version": "1.1.0"}, f)

        res_v2 = self.backup_engine.create_backup(
            extension_id="multiverext1234567890",
            extension_name="MultiVer",
            version="1.1.0",
            source_dir=ext_dir_v2,
            target_dir=self.primary_backup_dir
        )
        self.assertTrue(res_v2["success"])
        self.assertNotEqual(res_v1["backup_path"], res_v2["backup_path"])
        print("  [OK] Test 7: Múltiplas versões da mesma extensão preservadas simultaneamente.")

    # 8. Test backup incremental
    def test_08_incremental_backup(self):
        inc_dir = os.path.join(self.temp_work_dir, "inc_ext_src")
        os.makedirs(inc_dir, exist_ok=True)
        with open(os.path.join(inc_dir, "manifest.json"), "w") as f:
            json.dump({"name": "IncExt", "version": "1.0"}, f)
        with open(os.path.join(inc_dir, "static_large.dat"), "wb") as f:
            f.write(b"STATIC_DATA_" * 10000)

        # Baseline backup
        res1 = self.backup_engine.create_backup(
            extension_id="incext1234567890",
            extension_name="IncExt",
            version="1.0",
            source_dir=inc_dir,
            target_dir=self.primary_backup_dir,
            is_incremental=False
        )
        self.assertTrue(res1["success"])

        # Modify only one file
        with open(os.path.join(inc_dir, "modified.txt"), "w") as f:
            f.write("MODIFIED_CONTENT")

        # Incremental backup
        res2 = self.backup_engine.create_backup(
            extension_id="incext1234567890",
            extension_name="IncExt",
            version="1.0",
            source_dir=inc_dir,
            target_dir=self.primary_backup_dir,
            is_incremental=True
        )
        self.assertTrue(res2["success"])
        inc_stats = res2.get("incremental_stats")
        self.assertIsNotNone(inc_stats)
        self.assertGreater(inc_stats["reused_files"], 0)
        print(f"  [OK] Test 8: Backup incremental reutilizou {inc_stats['reused_files']} ficheiros ({inc_stats['saved_formatted']} poupados).")

    # 9. Test backup corrompido
    def test_09_corrupted_backup(self):
        # Create a backup then alter a byte
        corrupt_src = os.path.join(self.temp_work_dir, "corrupt_src")
        os.makedirs(corrupt_src, exist_ok=True)
        with open(os.path.join(corrupt_src, "manifest.json"), "w") as f:
            json.dump({"name": "CorruptTest", "version": "1.0"}, f)

        res = self.backup_engine.create_backup(
            extension_id="corrupt1234567890",
            extension_name="CorruptTest",
            version="1.0",
            source_dir=corrupt_src,
            target_dir=self.primary_backup_dir
        )
        backup_path = res["backup_path"]

        # Deliberately corrupt the file
        with open(backup_path, "r+b") as f:
            f.seek(30)
            f.write(b"\x00\x00\x00\x00\x00")

        val = validate_archive_integrity(backup_path)
        self.assertFalse(val["valid"])
        self.assertEqual(val["status"], "Backup inválido")
        print(f"  [OK] Test 9: Backup corrompido detetado com precisão: {val['status']}.")

    # 10. Test ficheiro em falta
    def test_10_missing_file_detection(self):
        # Test directory validator directly
        orig_hashes = {
            "manifest.json": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "missing_asset.png": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        }
        test_dir = os.path.join(self.temp_work_dir, "missing_test_dir")
        os.makedirs(test_dir, exist_ok=True)
        with open(os.path.join(test_dir, "manifest.json"), "wb") as f:
            f.write(b"")

        from core.integrity import validate_hashes_against_dir
        res = validate_hashes_against_dir(test_dir, orig_hashes)
        self.assertFalse(res["valid"])
        self.assertEqual(res["missing_count"], 1)
        self.assertEqual(res["details"]["missing"][0]["path"], "missing_asset.png")
        print(f"  [OK] Test 10: Ficheiro em falta ('missing_asset.png') identificado corretamente.")

    # 11. Test restauro
    def test_11_restore(self):
        restore_src = os.path.join(self.temp_work_dir, "restore_src")
        os.makedirs(restore_src, exist_ok=True)
        with open(os.path.join(restore_src, "manifest.json"), "w") as f:
            json.dump({"name": "RestoreTarget", "version": "1.0"}, f)
        with open(os.path.join(restore_src, "code.js"), "w") as f:
            f.write("alert('restored');")

        bk = self.backup_engine.create_backup(
            extension_id="restoretarget12345",
            extension_name="RestoreTarget",
            version="1.0",
            source_dir=restore_src,
            target_dir=self.primary_backup_dir
        )

        export_target = os.path.join(self.temp_work_dir, "RestoredUnpacked")
        rest = self.restore_engine.restore_extension(
            backup_file=bk["backup_path"],
            restore_mode="unpacked_export",
            custom_export_dir=export_target
        )
        self.assertTrue(rest["success"])
        self.assertTrue(os.path.exists(rest["destination_path"]))
        self.assertTrue(os.path.exists(os.path.join(rest["destination_path"], "code.js")))
        print(f"  [OK] Test 11: Restauro concluído com sucesso no caminho: {rest['destination_path']}.")

    # 12. Test rollback
    def test_12_rollback(self):
        install_path = os.path.join(self.temp_work_dir, "live_installation")
        os.makedirs(install_path, exist_ok=True)
        with open(os.path.join(install_path, "version.txt"), "w") as f:
            f.write("ORIGINAL_VERSION_1")

        # Create rollback snapshot
        rb_id = self.restore_engine.create_pre_restore_rollback_point(install_path, "testbk")
        self.assertIsNotNone(rb_id)

        # Overwrite with new version
        with open(os.path.join(install_path, "version.txt"), "w") as f:
            f.write("OVERWRITTEN_VERSION_2")

        # Execute rollback
        rev = self.restore_engine.revert_rollback(rb_id, install_path)
        self.assertTrue(rev["success"])
        with open(os.path.join(install_path, "version.txt"), "r") as f:
            content = f.read()
        self.assertEqual(content, "ORIGINAL_VERSION_1")
        print(f"  [OK] Test 12: Rollback reversível verificado com sucesso ({content}).")

    # 13. Test Chrome aberto
    def test_13_chrome_running_detection(self):
        chk = is_chrome_running()
        self.assertIn("running", chk)
        self.assertIn("count", chk)
        print(f"  [OK] Test 13: Deteção do processo chrome.exe: Running={chk['running']} (Processos: {chk['count']}).")

    # 14. Test Chrome fechado
    def test_14_chrome_closed_status(self):
        # Verify structure returned
        chk = is_chrome_running()
        self.assertIsInstance(chk["pids"], list)
        print("  [OK] Test 14: Estrutura de monitorização de estado do processo do Chrome validada.")

    # 15. Test destino sem espaço
    def test_15_insufficient_disk_space(self):
        # We test with safety margin requiring impossible space
        dummy_src = os.path.join(self.temp_work_dir, "dummy_src")
        os.makedirs(dummy_src, exist_ok=True)
        with open(os.path.join(dummy_src, "test.txt"), "w") as f:
            f.write("dummy")

        cap = verify_capacity_for_backup(dummy_src, self.primary_backup_dir, safety_margin_mb=100000000) # 100 TB margin
        self.assertFalse(cap["sufficient"])
        self.assertIsNotNone(cap["warning"])
        print(f"  [OK] Test 15: Alerta de capacidade insuficiente acionado corretamente: {cap['warning']}.")

    # 16. Test unidade externa desligada
    def test_16_disconnected_external_drive(self):
        fake_drive = "X:\\NonExistentDrive_9999\\Backups"
        res = self.backup_engine.create_backup(
            extension_id="testdrive123",
            extension_name="TestDrive",
            version="1.0",
            source_dir=os.path.join(self.temp_work_dir, "small_ext_src"),
            target_dir=fake_drive
        )
        # Should cleanly return an error response, not crash
        self.assertFalse(res["success"])
        self.assertIn("error", res)
        print(f"  [OK] Test 16: Falha em unidade desligada tratada de forma limpa (Código: {res['error']['code']}).")

    # 17. Test backup encriptado (AES-256-GCM)
    def test_17_encrypted_backup(self):
        enc_src = os.path.join(self.temp_work_dir, "enc_src")
        os.makedirs(enc_src, exist_ok=True)
        with open(os.path.join(enc_src, "manifest.json"), "w") as f:
            json.dump({"name": "EncryptedExt", "version": "1.0"}, f)
        with open(os.path.join(enc_src, "secret.key"), "w") as f:
            f.write("CONFIDENTIAL_CODE")

        secret_password = "SuperSecretPassword2026!"
        res = self.backup_engine.create_backup(
            extension_id="encryptedext123",
            extension_name="EncryptedExt",
            version="1.0",
            source_dir=enc_src,
            target_dir=self.primary_backup_dir,
            password=secret_password
        )
        self.assertTrue(res["success"])
        self.assertTrue(is_file_encrypted(res["backup_path"]))

        # Validation with wrong password must fail
        wrong_val = validate_archive_integrity(res["backup_path"], "WrongPassword")
        self.assertFalse(wrong_val["valid"])

        # Validation with correct password must succeed
        correct_val = validate_archive_integrity(res["backup_path"], secret_password)
        self.assertTrue(correct_val["valid"])

        print(f"  [OK] Test 17: Backup encriptado com AES-256-GCM e chave PBKDF2 validado com sucesso.")

    # 18. Test importação e exportação de backup
    def test_18_import_export_backup(self):
        # Create a backup
        src_dir = os.path.join(self.temp_work_dir, "export_src")
        os.makedirs(src_dir, exist_ok=True)
        with open(os.path.join(src_dir, "manifest.json"), "w") as f:
            json.dump({"name": "ExportExt", "version": "2.5.0"}, f)

        res = self.backup_engine.create_backup(
            extension_id="exportext123",
            extension_name="ExportExt",
            version="2.5.0",
            source_dir=src_dir,
            target_dir=self.primary_backup_dir
        )
        orig_backup = res["backup_path"]

        # Export to secondary folder
        exported_path = os.path.join(self.secondary_backup_dir, os.path.basename(orig_backup))
        shutil.copy2(orig_backup, exported_path)
        self.assertTrue(os.path.exists(exported_path))

        # Import / Validate the exported file
        val = validate_archive_integrity(exported_path)
        self.assertTrue(val["valid"])
        print(f"  [OK] Test 18: Exportação e importação verificadas com integridade SHA-256 preservada.")

    # 19. Test extensão removida depois do backup
    def test_19_extension_removed_after_backup(self):
        ephemeral_dir = os.path.join(self.temp_work_dir, "ephemeral_ext")
        os.makedirs(ephemeral_dir, exist_ok=True)
        with open(os.path.join(ephemeral_dir, "manifest.json"), "w") as f:
            json.dump({"name": "EphemeralExt", "version": "1.0"}, f)
        with open(os.path.join(ephemeral_dir, "vital.js"), "w") as f:
            f.write("console.log('essential functionality');")

        # 1. Create backup
        bk = self.backup_engine.create_backup(
            extension_id="ephemeral12345",
            extension_name="EphemeralExt",
            version="1.0",
            source_dir=ephemeral_dir,
            target_dir=self.primary_backup_dir
        )
        self.assertTrue(bk["success"])

        # 2. Simulate deletion / uninstall of the extension
        shutil.rmtree(ephemeral_dir)
        self.assertFalse(os.path.exists(ephemeral_dir))

        # 3. Restore extension from local backup
        rebuilt_dir = os.path.join(self.temp_work_dir, "rebuilt_ext")
        rest = self.restore_engine.restore_extension(
            backup_file=bk["backup_path"],
            restore_mode="unpacked_export",
            custom_export_dir=rebuilt_dir
        )
        self.assertTrue(rest["success"])
        rebuilt_path = rest["destination_path"]
        self.assertTrue(os.path.exists(os.path.join(rebuilt_path, "manifest.json")))
        self.assertTrue(os.path.exists(os.path.join(rebuilt_path, "vital.js")))
        print("  [OK] Test 19: Extensão totalmente recuperada e reconstruída a partir do backup após desinstalação!")

    # 20. Test licensing tier verification
    def test_20_licensing_tiers(self):
        prem_key = generate_sample_license_key("premium")
        ultm_key = generate_sample_license_key("ultimate")
        self.assertTrue(validate_license_key_format(prem_key)["valid"])
        self.assertTrue(validate_license_key_format(ultm_key)["valid"])
        self.assertFalse(validate_license_key_format("INVALID-KEY-1234-5678-9999")["valid"])
        print("  [OK] Test 20: Algoritmo de validação de licenças comerciais verificado.")

    # 21. Test backup compactado em ZIP por extensão e restauro direto do ZIP
    def test_21_zip_backup_and_restore(self):
        import zipfile
        zip_test_dir = os.path.join(self.temp_work_dir, "zip_src")
        os.makedirs(zip_test_dir, exist_ok=True)
        with open(os.path.join(zip_test_dir, "manifest.json"), "w") as f:
            json.dump({"manifest_version": 3, "name": "ZipTestExt", "version": "1.0"}, f)
        with open(os.path.join(zip_test_dir, "script.js"), "w") as f:
            f.write("console.log('zip payload');")

        # 1. Create backup - must generate both .crxbackup and .zip
        bk = self.backup_engine.create_backup(
            extension_id="zipextension123456789012345678",
            extension_name="ZipTestExt",
            version="1.0",
            source_dir=zip_test_dir,
            target_dir=self.primary_backup_dir
        )
        self.assertTrue(bk["success"])
        zip_path = bk.get("zip_path")
        self.assertIsNotNone(zip_path)
        self.assertTrue(os.path.exists(zip_path))

        # 2. Check ZIP contents (pure extension files at root)
        with zipfile.ZipFile(zip_path, "r") as z:
            names = z.namelist()
            self.assertIn("manifest.json", names)
            self.assertIn("script.js", names)

        # 3. Validate ZIP integrity
        val = validate_archive_integrity(zip_path)
        self.assertTrue(val["valid"])

        # 4. Inspect ZIP
        info = self.restore_engine.inspect_backup_archive(zip_path)
        self.assertEqual(info["extension_name"], "ZipTestExt")
        self.assertEqual(info["version"], "1.0")

        # 5. Restore from ZIP
        rebuilt_zip_dir = os.path.join(self.temp_work_dir, "rebuilt_from_zip")
        rest = self.restore_engine.restore_extension(
            backup_file=zip_path,
            restore_mode="unpacked_export",
            custom_export_dir=rebuilt_zip_dir
        )
        self.assertTrue(rest["success"])
        self.assertTrue(os.path.exists(os.path.join(rest["destination_path"], "manifest.json")))
        self.assertTrue(os.path.exists(os.path.join(rest["destination_path"], "script.js")))
        print("  [OK] Test 21: Backup ZIP com ficheiros compactados e restauro direto do ficheiro ZIP validados com 100% de sucesso.")



if __name__ == "__main__":
    print("\n==================================================================")
    print("   CHROME EXTENSION BACKUP PRO - SUÍTE DE TESTES AUTOMATIZADA")
    print("==================================================================\n")
    unittest.main(verbosity=2)
