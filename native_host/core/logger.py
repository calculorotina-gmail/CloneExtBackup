"""
Local structured logging system for Chrome Extension Backup Pro.
Maintains daily log files (Logs/YYYY-MM-DD.log), redacts passwords/sensitive data,
and provides log export functionality for technical support.
"""

import os
import re
import datetime
from pathlib import Path

DEFAULT_LOGS_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "ChromeExtBackupPro",
    "Logs"
)


class HostLogger:
    def __init__(self, logs_dir: str = None):
        if logs_dir is None:
            self.logs_dir = DEFAULT_LOGS_DIR
        else:
            self.logs_dir = logs_dir
        
        os.makedirs(self.logs_dir, exist_ok=True)
        self._sensitive_patterns = [
            re.compile(r'(password|pass|secret|token|key)["\s:=]+([^\s,;"]+)', re.IGNORECASE)
        ]

    def _get_current_log_path(self) -> str:
        today = datetime.date.today().strftime("%Y-%m-%d")
        return os.path.join(self.logs_dir, f"{today}.log")

    def _sanitize(self, message: str) -> str:
        """Sanitizes sensitive information such as encryption passwords or auth tokens."""
        if not message:
            return ""
        sanitized = message
        for pat in self._sensitive_patterns:
            sanitized = pat.sub(r'\1: [REDACTED]', sanitized)
        return sanitized

    def _write_entry(self, level: str, message: str, operation: str = ""):
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            clean_msg = self._sanitize(message)
            op_part = f" [{operation}]" if operation else ""
            line = f"[{timestamp}] [{level.upper():5s}]{op_part} {clean_msg}\n"
            
            with open(self._get_current_log_path(), "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass  # Avoid crashing the application if disk log writing fails temporarily

    def info(self, message: str, operation: str = ""):
        self._write_entry("INFO", message, operation)

    def warn(self, message: str, operation: str = ""):
        self._write_entry("WARN", message, operation)

    def error(self, message: str, operation: str = ""):
        self._write_entry("ERROR", message, operation)

    def debug(self, message: str, operation: str = ""):
        self._write_entry("DEBUG", message, operation)

    def get_logs(self, limit_lines: int = 500) -> list[str]:
        """Returns recent log lines from the current day's log file."""
        log_path = self._get_current_log_path()
        if not os.path.exists(log_path):
            return []
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                return [line.strip() for line in lines[-limit_lines:]]
        except Exception as e:
            return [f"Erro ao ler ficheiro de log: {e}"]

    def export_logs(self, target_file: str) -> bool:
        """Exports all log files into a single consolidated diagnostic file."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(target_file)), exist_ok=True)
            with open(target_file, "w", encoding="utf-8") as out_f:
                out_f.write(f"=== CHROME EXTENSION BACKUP PRO - DIAGNOSTIC LOG EXPORT ===\n")
                out_f.write(f"Export Date: {datetime.datetime.now().isoformat()}\n\n")
                
                log_files = sorted(Path(self.logs_dir).glob("*.log"), reverse=True)
                for log_file in log_files:
                    out_f.write(f"\n--- LOG FILE: {log_file.name} ---\n")
                    with open(log_file, "r", encoding="utf-8", errors="replace") as in_f:
                        out_f.write(in_f.read())
            return True
        except Exception:
            return False


# Singleton instance for convenience
logger = HostLogger()
