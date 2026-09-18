"""
Process Manager for Chrome running detection and controlled termination on Windows.
Strictly adheres to requirement 10:
- Detects if Chrome is running
- Explains lock risks
- Provides controlled soft-close when authorized by the user
- Never terminates processes silently
"""

import subprocess
import time
import os
from typing import Dict, Any, List


def is_chrome_running() -> Dict[str, Any]:
    """
    Detects if chrome.exe is currently running on Windows.
    Returns process count and PID list.
    """
    if os.name != 'nt':
        return {"running": False, "pids": [], "count": 0}

    try:
        # Run tasklist to find chrome.exe
        cmd = ["tasklist", "/FO", "CSV", "/NH", "/FI", "IMAGENAME eq chrome.exe"]
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        output = res.stdout.strip()
        pids: List[int] = []
        if output and "chrome.exe" in output.lower():
            for line in output.splitlines():
                parts = [p.strip(' "') for p in line.split('","')]
                if len(parts) >= 2 and parts[0].lower() == "chrome.exe":
                    try:
                        pids.append(int(parts[1]))
                    except ValueError:
                        continue

        return {
            "running": len(pids) > 0,
            "count": len(pids),
            "pids": pids,
            "message": f"O Google Chrome está em execução com {len(pids)} processos ativos." if pids else "O Google Chrome não está em execução."
        }
    except Exception as e:
        return {
            "running": False,
            "count": 0,
            "pids": [],
            "error": str(e),
            "message": f"Erro ao verificar processos do Chrome: {e}"
        }


def request_graceful_chrome_close(timeout_seconds: int = 8) -> Dict[str, Any]:
    """
    Attempts a controlled soft-close of Google Chrome.
    Invokes taskkill /im chrome.exe (graceful WM_CLOSE request), waits for exit,
    and re-verifies process state.
    """
    initial_check = is_chrome_running()
    if not initial_check["running"]:
        return {
            "success": True,
            "closed": True,
            "message": "O Google Chrome já estava fechado."
        }

    try:
        # First send graceful close
        subprocess.run(
            ["taskkill", "/IM", "chrome.exe"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )

        # Poll for process exit
        start = time.time()
        while time.time() - start < timeout_seconds:
            time.sleep(0.6)
            check = is_chrome_running()
            if not check["running"]:
                return {
                    "success": True,
                    "closed": True,
                    "message": "O Google Chrome foi fechado com sucesso de forma controlada."
                }

        # If still running after timeout, report that it did not close
        final_check = is_chrome_running()
        return {
            "success": not final_check["running"],
            "closed": not final_check["running"],
            "remaining_count": final_check["count"],
            "message": "Algumas instâncias do Chrome ainda não terminaram. O utilizador pode precisar de fechar separadores ou confirmar o encerramento no navegador."
        }
    except Exception as e:
        return {
            "success": False,
            "closed": False,
            "error": str(e),
            "message": f"Erro ao solicitar encerramento do Chrome: {e}"
        }
