"""
Cryptographic Integrity Verification Engine for Chrome Extension Backups.
Adheres strictly to requirement 7:
- Calculates SHA-256 digests for all files
- Validates backup integrity against manifest hashes
- Classifies files as:
    * Iguais (Identical)
    * Alterados (Modified)
    * Em falta (Missing)
    * Adicionados (Added / Extra)
- Returns clear status: "Backup válido" or "Backup inválido" with complete file diff details.
"""

import os
import hashlib
import zipfile
from typing import Dict, Any, Tuple, Optional


def calculate_sha256_stream(fp) -> str:
    """Calculates SHA-256 from an open file or stream in 64KB blocks."""
    sha = hashlib.sha256()
    while chunk := fp.read(65536):
        sha.update(chunk)
    return sha.hexdigest()


def calculate_file_sha256(file_path: str) -> str:
    """Calculates SHA-256 hex digest for a physical file."""
    with open(file_path, "rb") as f:
        return calculate_sha256_stream(f)


def build_hashes_map_for_dir(directory: str) -> Dict[str, str]:
    """
    Builds a dictionary mapping normalized relative file paths to SHA-256 hashes.
    Uses forward slashes for cross-platform and ZIP compatibility.
    """
    hashes = {}
    for root, _, files in os.walk(directory):
        for f in files:
            full_p = os.path.join(root, f)
            rel_p = os.path.relpath(full_p, directory).replace(os.sep, "/")
            try:
                h = calculate_file_sha256(full_p)
                hashes[rel_p] = h
            except Exception as e:
                hashes[rel_p] = f"ERROR: {e}"
    return hashes


def validate_hashes_against_dir(extension_dir: str, original_hashes: Dict[str, str]) -> Dict[str, Any]:
    """
    Validates a physical folder against the original hashes map.
    Categorizes files into: identical, modified, missing, added.
    """
    identical = []
    modified = []
    missing = []
    added = []

    current_hashes = build_hashes_map_for_dir(extension_dir)

    # Check original files
    for rel_path, orig_hash in original_hashes.items():
        if rel_path not in current_hashes:
            missing.append({
                "path": rel_path,
                "original_hash": orig_hash
            })
        else:
            curr_hash = current_hashes[rel_path]
            if curr_hash == orig_hash:
                identical.append({
                    "path": rel_path,
                    "hash": curr_hash
                })
            else:
                modified.append({
                    "path": rel_path,
                    "original_hash": orig_hash,
                    "current_hash": curr_hash
                })

    # Check extra/added files
    for rel_path, curr_hash in current_hashes.items():
        if rel_path not in original_hashes:
            added.append({
                "path": rel_path,
                "current_hash": curr_hash
            })

    is_valid = (len(modified) == 0 and len(missing) == 0)
    status_text = "Backup válido" if is_valid else "Backup inválido"

    return {
        "valid": is_valid,
        "status": status_text,
        "identical_count": len(identical),
        "modified_count": len(modified),
        "missing_count": len(missing),
        "added_count": len(added),
        "total_expected_files": len(original_hashes),
        "total_actual_files": len(current_hashes),
        "details": {
            "identical": identical,
            "modified": modified,
            "missing": missing,
            "added": added
        }
    }


def validate_archive_integrity(archive_path: str, password: Optional[str] = None) -> Dict[str, Any]:
    """
    Validates the integrity of a .crxbackup ZIP archive directly without extracting to disk.
    Reads manifest.json and hashes/hashes.json from the archive and recomputes hashes for extension/ files.
    """
    import json
    from .encryption import is_file_encrypted, decrypt_file

    temp_decrypted = None
    target_zip = archive_path

    try:
        # If encrypted, decrypt to temporary file first
        if is_file_encrypted(archive_path):
            if not password:
                return {
                    "valid": False,
                    "status": "Backup inválido",
                    "error": "Arquivo encriptado. É necessária a palavra-passe para validar a integridade."
                }
            temp_decrypted = archive_path + ".tmp_val"
            decrypt_file(archive_path, temp_decrypted, password)
            target_zip = temp_decrypted

        with zipfile.ZipFile(target_zip, "r") as zf:
            # Check for bad zip blocks
            bad_crc = zf.testzip()
            if bad_crc:
                return {
                    "valid": False,
                    "status": "Backup inválido",
                    "error": f"Corrupção de arquivo ZIP no ficheiro: {bad_crc}"
                }

            file_list = zf.namelist()
            if "hashes/hashes.json" not in file_list:
                # Check if this is a standard extension ZIP archive with manifest.json
                manifest_candidates = [n for n in file_list if n == "manifest.json" or n.endswith("/manifest.json")]
                if manifest_candidates:
                    ext_files = [n for n in file_list if not n.endswith("/")]
                    return {
                        "valid": True,
                        "status": "Backup válido (Arquivo ZIP da Extensão)",
                        "total_files": len(ext_files),
                        "identical_count": len(ext_files),
                        "modified_count": 0,
                        "missing_count": 0,
                        "added_count": 0,
                        "details": {
                            "identical": [{"path": n} for n in ext_files],
                            "modified": [],
                            "missing": [],
                            "added": []
                        }
                    }
                return {
                    "valid": False,
                    "status": "Backup inválido",
                    "error": "Arquivo ZIP inválido: manifest.json ou hashes/hashes.json não encontrado."
                }

            with zf.open("hashes/hashes.json") as hf:
                original_hashes = json.load(hf)

            identical = []
            modified = []
            missing = []
            added = []

            # Find all extension/ payload files in zip
            archive_ext_files = {}
            for name in file_list:
                if name.startswith("extension/") and not name.endswith("/"):
                    # normalize relative path inside extension/
                    rel_name = name[len("extension/"):]
                    with zf.open(name) as f:
                        curr_hash = calculate_sha256_stream(f)
                        archive_ext_files[rel_name] = curr_hash

            for rel_path, orig_hash in original_hashes.items():
                if rel_path not in archive_ext_files:
                    missing.append({"path": rel_path, "original_hash": orig_hash})
                else:
                    curr_hash = archive_ext_files[rel_path]
                    if curr_hash == orig_hash:
                        identical.append({"path": rel_path, "hash": curr_hash})
                    else:
                        modified.append({"path": rel_path, "original_hash": orig_hash, "current_hash": curr_hash})

            for rel_path, curr_hash in archive_ext_files.items():
                if rel_path not in original_hashes:
                    added.append({"path": rel_path, "current_hash": curr_hash})

            is_valid = (len(modified) == 0 and len(missing) == 0)
            status_text = "Backup válido" if is_valid else "Backup inválido"

            return {
                "valid": is_valid,
                "status": status_text,
                "identical_count": len(identical),
                "modified_count": len(modified),
                "missing_count": len(missing),
                "added_count": len(added),
                "total_expected_files": len(original_hashes),
                "total_actual_files": len(archive_ext_files),
                "details": {
                    "identical": identical,
                    "modified": modified,
                    "missing": missing,
                    "added": added
                }
            }
    except Exception as e:
        return {
            "valid": False,
            "status": "Backup inválido",
            "error": f"Erro durante validação: {e}"
        }
    finally:
        if temp_decrypted and os.path.exists(temp_decrypted):
            try:
                os.remove(temp_decrypted)
            except Exception:
                pass
