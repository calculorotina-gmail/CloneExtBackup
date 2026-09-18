"""
Backup and Version Comparison Engine.
Adheres strictly to requirement 20:
- Compares two backup versions or a backup vs current installation
- Categorizes:
    * Ficheiros adicionados (Added)
    * Ficheiros removidos (Removed)
    * Ficheiros alterados (Modified)
    * Ficheiros iguais (Identical)
- Compares file sizes and SHA-256 hashes
"""

import os
import json
import zipfile
from typing import Dict, Any, Optional
from .integrity import build_hashes_map_for_dir, calculate_file_sha256
from .encryption import is_file_encrypted, decrypt_file
from .disk_space import format_bytes


def extract_manifest_and_hashes_from_archive(archive_path: str, password: Optional[str] = None) -> Dict[str, Any]:
    """Reads manifest.json and hashes/hashes.json from a .crxbackup without full extraction."""
    temp_dec = None
    target_zip = archive_path
    try:
        if is_file_encrypted(archive_path):
            if not password:
                raise ValueError("Arquivo encriptado. Palavra-passe necessária para comparação.")
            temp_dec = archive_path + ".tmp_cmp"
            decrypt_file(archive_path, temp_dec, password)
            target_zip = temp_dec

        with zipfile.ZipFile(target_zip, "r") as zf:
            manifest_data = {}
            if "manifest.json" in zf.namelist():
                with zf.open("manifest.json") as mf:
                    manifest_data = json.load(mf)

            hashes_data = {}
            if "hashes/hashes.json" in zf.namelist():
                with zf.open("hashes/hashes.json") as hf:
                    hashes_data = json.load(hf)

            file_sizes = {}
            for info in zf.infolist():
                if info.filename.startswith("extension/") and not info.is_dir():
                    rel = info.filename[len("extension/"):]
                    file_sizes[rel] = info.file_size

            return {
                "manifest": manifest_data,
                "hashes": hashes_data,
                "sizes": file_sizes
            }
    finally:
        if temp_dec and os.path.exists(temp_dec):
            try:
                os.remove(temp_dec)
            except Exception:
                pass


def compare_two_versions(
    item_a_path: str,
    item_b_path: str,
    password_a: Optional[str] = None,
    password_b: Optional[str] = None
) -> Dict[str, Any]:
    """
    Compares version A with version B. Supports comparing two .crxbackup archives
    or a .crxbackup archive against a live extension directory.
    """
    # Load A
    if os.path.isdir(item_a_path):
        hashes_a = build_hashes_map_for_dir(item_a_path)
        sizes_a = {rel: os.path.getsize(os.path.join(item_a_path, rel.replace("/", os.sep))) for rel in hashes_a}
        label_a = f"Pasta Local ({os.path.basename(item_a_path)})"
        version_a = "Instalação Atual"
    else:
        info_a = extract_manifest_and_hashes_from_archive(item_a_path, password_a)
        hashes_a = info_a["hashes"]
        sizes_a = info_a["sizes"]
        label_a = info_a["manifest"].get("backup_id", os.path.basename(item_a_path))
        version_a = info_a["manifest"].get("version", "A")

    # Load B
    if os.path.isdir(item_b_path):
        hashes_b = build_hashes_map_for_dir(item_b_path)
        sizes_b = {rel: os.path.getsize(os.path.join(item_b_path, rel.replace("/", os.sep))) for rel in hashes_b}
        label_b = f"Pasta Local ({os.path.basename(item_b_path)})"
        version_b = "Instalação Atual"
    else:
        info_b = extract_manifest_and_hashes_from_archive(item_b_path, password_b)
        hashes_b = info_b["hashes"]
        sizes_b = info_b["sizes"]
        label_b = info_b["manifest"].get("backup_id", os.path.basename(item_b_path))
        version_b = info_b["manifest"].get("version", "B")

    added = []
    removed = []
    modified = []
    identical = []

    # Check all files in A
    for path, hash_a in hashes_a.items():
        size_a = sizes_a.get(path, 0)
        if path not in hashes_b:
            removed.append({
                "path": path,
                "size_a": size_a,
                "size_a_formatted": format_bytes(size_a),
                "hash_a": hash_a
            })
        else:
            hash_b = hashes_b[path]
            size_b = sizes_b.get(path, 0)
            if hash_a == hash_b:
                identical.append({
                    "path": path,
                    "size": size_a,
                    "size_formatted": format_bytes(size_a),
                    "hash": hash_a
                })
            else:
                diff_bytes = size_b - size_a
                modified.append({
                    "path": path,
                    "size_a": size_a,
                    "size_b": size_b,
                    "size_a_formatted": format_bytes(size_a),
                    "size_b_formatted": format_bytes(size_b),
                    "diff_bytes": diff_bytes,
                    "diff_formatted": ("+" if diff_bytes > 0 else "") + format_bytes(diff_bytes),
                    "hash_a": hash_a,
                    "hash_b": hash_b
                })

    # Check files in B not in A (Added)
    for path, hash_b in hashes_b.items():
        if path not in hashes_a:
            size_b = sizes_b.get(path, 0)
            added.append({
                "path": path,
                "size_b": size_b,
                "size_b_formatted": format_bytes(size_b),
                "hash_b": hash_b
            })

    total_size_a = sum(sizes_a.values())
    total_size_b = sum(sizes_b.values())
    net_diff = total_size_b - total_size_a

    return {
        "success": True,
        "label_a": label_a,
        "version_a": version_a,
        "label_b": label_b,
        "version_b": version_b,
        "counts": {
            "identical": len(identical),
            "modified": len(modified),
            "added": len(added),
            "removed": len(removed)
        },
        "metrics": {
            "total_files_a": len(hashes_a),
            "total_files_b": len(hashes_b),
            "total_size_a_bytes": total_size_a,
            "total_size_a_formatted": format_bytes(total_size_a),
            "total_size_b_bytes": total_size_b,
            "total_size_b_formatted": format_bytes(total_size_b),
            "net_difference_bytes": net_diff,
            "net_difference_formatted": ("+" if net_diff > 0 else "") + format_bytes(net_diff)
        },
        "details": {
            "added": added,
            "removed": removed,
            "modified": modified,
            "identical": identical
        }
    }
