"""
Compression Engine for Chrome Extension Backup Archives (.crxbackup).
Supports:
- No compression (ZIP_STORED)
- Normal compression (ZIP_DEFLATED level 6)
- Maximum compression (ZIP_DEFLATED level 9)
Provides uncompressed vs compressed metrics, integrity testzip verification, and extraction.
"""

import os
import zipfile
from typing import Dict, Any, List, Optional
from .disk_space import format_bytes


class BackupCompressor:
    def __init__(self, level: int = 6):
        """
        level:
          0 = No compression (Stored)
          1..6 = Normal compression (Deflated level 6)
          7..9 = Maximum compression (Deflated level 9)
        """
        self.level = level
        if level == 0:
            self.compression_type = zipfile.ZIP_STORED
            self.compresslevel = None
        elif level >= 7:
            self.compression_type = zipfile.ZIP_DEFLATED
            self.compresslevel = 9
        else:
            self.compression_type = zipfile.ZIP_DEFLATED
            self.compresslevel = 6

    def create_archive(self, source_dir: str, target_archive_path: str) -> Dict[str, Any]:
        """
        Packs the contents of source_dir into a single .crxbackup ZIP archive.
        Preserves relative directory hierarchy and file attributes.
        """
        os.makedirs(os.path.dirname(os.path.abspath(target_archive_path)), exist_ok=True)

        uncompressed_size = 0
        file_count = 0

        # Open zip archive with specified compression
        kwargs = {"compression": self.compression_type}
        if self.compresslevel is not None:
            kwargs["compresslevel"] = self.compresslevel

        with zipfile.ZipFile(target_archive_path, "w", **kwargs) as zf:
            for root, _, files in os.walk(source_dir):
                for f in files:
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, source_dir)
                    try:
                        file_size = os.path.getsize(full_p)
                        uncompressed_size += file_size
                        zf.write(full_p, arcname=rel_p.replace(os.sep, "/"))
                        file_count += 1
                    except Exception as e:
                        raise IOError(f"Falha ao arquivar ficheiro {rel_p}: {e}")

        # Verify integrity of written zip after closing/flushing
        with zipfile.ZipFile(target_archive_path, "r") as zf_verify:
            bad_file = zf_verify.testzip()
            if bad_file:
                raise IOError(f"Ficheiro corrompido durante a escrita do arquivo ZIP: {bad_file}")

        compressed_size = os.path.getsize(target_archive_path)
        saved_bytes = max(0, uncompressed_size - compressed_size)
        ratio_pct = (saved_bytes / uncompressed_size * 100.0) if uncompressed_size > 0 else 0.0

        return {
            "archive_path": target_archive_path,
            "file_count": file_count,
            "uncompressed_bytes": uncompressed_size,
            "uncompressed_formatted": format_bytes(uncompressed_size),
            "compressed_bytes": compressed_size,
            "compressed_formatted": format_bytes(compressed_size),
            "saved_bytes": saved_bytes,
            "saved_formatted": format_bytes(saved_bytes),
            "ratio_percent": round(ratio_pct, 1),
            "compression_level": self.level
        }

    def extract_archive(self, archive_path: str, target_dir: str) -> Dict[str, Any]:
        """
        Extracts all files from .crxbackup ZIP archive to target_dir.
        Checks for path traversal vulnerabilities (Zip Slip).
        """
        if not os.path.exists(archive_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {archive_path}")

        os.makedirs(target_dir, exist_ok=True)
        extracted_count = 0
        total_extracted_bytes = 0

        with zipfile.ZipFile(archive_path, "r") as zf:
            # Check integrity first
            bad_file = zf.testzip()
            if bad_file:
                raise IOError(f"Arquivo de backup corrompido: {bad_file}")

            for member in zf.infolist():
                # Security: prevent path traversal (Zip Slip vulnerability)
                member_path = member.filename.replace("/", os.sep)
                norm_target = os.path.abspath(target_dir)
                dest_path = os.path.abspath(os.path.join(target_dir, member_path))

                if not dest_path.startswith(norm_target):
                    raise PermissionError(f"Tentativa de travessia de caminho (Zip Slip) detetada: {member.filename}")

                zf.extract(member, target_dir)
                extracted_count += 1
                total_extracted_bytes += member.file_size

        return {
            "extracted_count": extracted_count,
            "total_bytes": total_extracted_bytes,
            "total_formatted": format_bytes(total_extracted_bytes),
            "target_dir": target_dir
        }
