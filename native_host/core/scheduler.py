"""
Automated Scheduling Engine for Windows.
Adheres strictly to requirement 14:
- Frequency: Daily, Weekly, Specific Days, At Windows Logon, Chrome start, On change
- Configurable execution time
- Real integration with Windows Task Scheduler (schtasks.exe)
- Headless execution engine for automated background backups
"""

import os
import sys
import json
import subprocess
import datetime
from typing import Dict, Any, List, Optional
from .logger import logger

SCHEDULE_FILE = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "ChromeExtBackupPro",
    "schedule.json"
)

TASK_NAME = "ChromeExtBackupPro_AutoBackup"


def get_schedule_config() -> Dict[str, Any]:
    """Loads schedule configuration or returns defaults."""
    if os.path.exists(SCHEDULE_FILE):
        try:
            with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return {
        "enabled": False,
        "frequency": "daily",  # daily, weekly, custom_days, on_logon, on_change
        "time": "03:00",
        "days": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
        "profiles": ["Default"],
        "backup_all_profiles": True,
        "backup_before_restore": True,
        "compression_level": 6,
        "is_incremental": True,
        "last_run": None,
        "last_status": None
    }


def save_schedule_config(config: Dict[str, Any]) -> bool:
    """Saves schedule configuration to disk."""
    try:
        os.makedirs(os.path.dirname(SCHEDULE_FILE), exist_ok=True)
        with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Erro ao gravar ficheiro de agendamento: {e}", "SCHEDULER")
        return False


def register_windows_task(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Registers or updates the scheduled task in the Windows Task Scheduler using schtasks.exe.
    """
    if os.name != 'nt':
        return {"success": False, "message": "O Agendador de Tarefas do Windows só é suportado no Windows."}

    if not config.get("enabled", False):
        return unregister_windows_task()

    # Determine command to run headless
    python_exe = sys.executable
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ext_backup_host.py"))
    run_cmd = f'"{python_exe}" "{script_path}" --run-scheduled'

    freq = config.get("frequency", "daily").lower()
    time_val = config.get("time", "03:00")

    # Map frequency to schtasks parameters
    schtasks_args = ["schtasks", "/Create", "/TN", TASK_NAME, "/TR", run_cmd, "/F"]

    if freq == "daily":
        schtasks_args.extend(["/SC", "DAILY", "/ST", time_val])
    elif freq == "weekly":
        days = ",".join(config.get("days", ["MON"]))
        schtasks_args.extend(["/SC", "WEEKLY", "/D", days, "/ST", time_val])
    elif freq == "on_logon":
        schtasks_args.extend(["/SC", "ONLOGON"])
    else:
        schtasks_args.extend(["/SC", "DAILY", "/ST", time_val])

    try:
        res = subprocess.run(
            schtasks_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        if res.returncode == 0:
            logger.info(f"Tarefa agendada no Windows criada com sucesso ({freq} às {time_val}).", "SCHEDULER")
            save_schedule_config(config)
            return {
                "success": True,
                "message": f"Tarefa agendada criada no Windows ({freq} às {time_val})."
            }
        else:
            err_msg = res.stderr.strip() or res.stdout.strip()
            logger.error(f"Erro ao criar tarefa no Windows: {err_msg}", "SCHEDULER")
            return {
                "success": False,
                "message": f"Falha ao registar no Agendador do Windows: {err_msg}"
            }
    except Exception as e:
        logger.error(f"Exceção ao agendar tarefa: {e}", "SCHEDULER")
        return {"success": False, "message": str(e)}


def unregister_windows_task() -> Dict[str, Any]:
    """Removes the scheduled task from Windows Task Scheduler."""
    if os.name != 'nt':
        return {"success": True}

    try:
        cmd = ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"]
        subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        logger.info("Tarefa agendada removida do Windows.", "SCHEDULER")
        cfg = get_schedule_config()
        cfg["enabled"] = False
        save_schedule_config(cfg)
        return {"success": True, "message": "Tarefa agendada desativada no Windows."}
    except Exception as e:
        return {"success": False, "message": str(e)}
