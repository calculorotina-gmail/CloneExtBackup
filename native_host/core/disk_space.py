"""
Disk Space Detection and Estimation Module for Windows.
Verifies target drive free space before backup operations, estimates required size,
and raises warnings or blocks operations when capacity is insufficient.
"""

import os
import shutil
import ctypes
from typing import Tuple, Dict, Any


def format_bytes(size_bytes: int) -> str:
    """Formats bytes into human-readable string (e.g. 14.5 MB, 1.2 GB)."""
    if size_bytes < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_idx = 0
    val = float(size_bytes)
    while val >= 1024.0 and unit_idx < len(units) - 1:
        val /= 1024.0
        unit_idx += 1
    return f"{val:.2f} {units[unit_idx]}" if unit_idx > 0 else f"{int(val)} B"


def get_disk_free_space(path: str) -> Dict[str, Any]:
    """
    Returns total, free, and used space for the drive containing path.
    Uses Windows GetDiskFreeSpaceExW for native accuracy on Windows.
    """
    abs_path = os.path.abspath(path)
    
    # Ensure directory exists or walk up to existing parent
    curr = abs_path
    while not os.path.exists(curr) and os.path.dirname(curr) != curr:
        curr = os.path.dirname(curr)
    
    if os.name == 'nt':
        try:
            free_bytes_available = ctypes.c_ulonglong()
            total_number_of_bytes = ctypes.c_ulonglong()
            total_number_of_free_bytes = ctypes.c_ulonglong()
            
            ret = ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(curr),
                ctypes.byref(free_bytes_available),
                ctypes.byref(total_number_of_bytes),
                ctypes.byref(total_number_of_free_bytes)
            )
            if ret != 0:
                total = total_number_of_bytes.value
                free = free_bytes_available.value
                used = total - free
                pct = (used / total * 100.0) if total > 0 else 0.0
                return {
                    "total_bytes": total,
                    "free_bytes": free,
                    "used_bytes": used,
                    "used_percent": round(pct, 1),
                    "total_formatted": format_bytes(total),
                    "free_formatted": format_bytes(free),
                    "used_formatted": format_bytes(used),
                    "drive": os.path.splitdrive(curr)[0] or curr
                }
        except Exception:
            pass

    # Fallback to shutil.disk_usage
    try:
        usage = shutil.disk_usage(curr)
        pct = (usage.used / usage.total * 100.0) if usage.total > 0 else 0.0
        return {
            "total_bytes": usage.total,
            "free_bytes": usage.free,
            "used_bytes": usage.used,
            "used_percent": round(pct, 1),
            "total_formatted": format_bytes(usage.total),
            "free_formatted": format_bytes(usage.free),
            "used_formatted": format_bytes(usage.used),
            "drive": os.path.splitdrive(curr)[0] or curr
        }
    except Exception as e:
        return {
            "total_bytes": 0,
            "free_bytes": 0,
            "used_bytes": 0,
            "used_percent": 0.0,
            "total_formatted": "Desconhecido",
            "free_formatted": "Desconhecido",
            "used_formatted": "Desconhecido",
            "drive": curr,
            "error": str(e)
        }


def calculate_dir_size_and_count(dir_path: str) -> Tuple[int, int]:
    """Calculates total bytes and file count for a directory."""
    if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
        return 0, 0

    total_bytes = 0
    file_count = 0
    for root, _, files in os.walk(dir_path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total_bytes += os.path.getsize(fp)
                file_count += 1
            except (OSError, FileNotFoundError):
                continue
    return total_bytes, file_count


def verify_capacity_for_backup(source_dir: str, target_dir: str, compression_level: int = 6, safety_margin_mb: int = 50) -> Dict[str, Any]:
    """
    Checks if target drive has sufficient space to store the backup.
    Applies estimated compression ratio and 50MB headroom safety margin.
    """
    src_size, file_count = calculate_dir_size_and_count(source_dir)
    
    # Compression ratio estimation
    ratio = 1.0 if compression_level == 0 else (0.65 if compression_level <= 6 else 0.50)
    estimated_backup_size = int(src_size * ratio) + 10240  # +10KB for manifests
    margin_bytes = safety_margin_mb * 1024 * 1024
    required_bytes = estimated_backup_size + margin_bytes

    disk_info = get_disk_free_space(target_dir)
    free_bytes = disk_info.get("free_bytes", 0)

    sufficient = (free_bytes >= required_bytes)

    return {
        "sufficient": sufficient,
        "source_size_bytes": src_size,
        "source_size_formatted": format_bytes(src_size),
        "source_file_count": file_count,
        "estimated_backup_bytes": estimated_backup_size,
        "estimated_backup_formatted": format_bytes(estimated_backup_size),
        "required_with_margin_bytes": required_bytes,
        "required_with_margin_formatted": format_bytes(required_bytes),
        "target_free_bytes": free_bytes,
        "target_free_formatted": format_bytes(free_bytes),
        "target_drive": disk_info.get("drive", target_dir),
        "warning": None if sufficient else f"Espaço insuficiente na unidade {disk_info.get('drive')}. Disponível: {format_bytes(free_bytes)}, Necessário estimado: {format_bytes(required_bytes)}."
    }
