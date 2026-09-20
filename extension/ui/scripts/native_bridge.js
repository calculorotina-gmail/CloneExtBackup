/**
 * Chrome Extension Backup Pro - Native Bridge
 * Communicates directly with the Windows Native Messaging Host ("com.extbackup.pro")
 * or relays through the background service worker when necessary.
 */

class NativeBridge {
  constructor() {
    this.isConnected = false;
    this.listeners = [];
  }

  onConnectionChange(cb) {
    this.listeners.push(cb);
  }

  _notifyConnection(status) {
    this.isConnected = status;
    this.listeners.forEach((cb) => {
      try {
        cb(status);
      } catch (e) {
        console.warn("Erro no listener de conexão:", e);
      }
    });
  }

  /**
   * Sends a command request to the native messaging host.
   */
  async send(action, payload = {}, timeoutMs = 45000) {
    return new Promise((resolve, reject) => {
      let isSettled = false;

      const timer = setTimeout(() => {
        if (!isSettled) {
          isSettled = true;
          this._notifyConnection(false);
          reject(new Error(`Tempo limite excedido para a ação '${action}' (${timeoutMs / 1000}s)`));
        }
      }, timeoutMs);

      const handleResponse = (response) => {
        if (isSettled) return;
        isSettled = true;
        clearTimeout(timer);

        if (chrome.runtime.lastError) {
          this._notifyConnection(false);
          let msg = chrome.runtime.lastError.message || "";
          if (msg.includes("Specified native messaging host not found")) {
            msg = "Componente local Windows não encontrado. Execute 'install_host.bat' na pasta native_host para registar o host nativo.";
          }
          return reject(new Error(msg));
        }

        if (!response) {
          this._notifyConnection(false);
          return reject(new Error("Resposta vazia do componente local. Verifique se o instalador 'install_host.bat' foi executado."));
        }

        if (response.error && (response.error.code === "NT-0001" || response.error.code === "NT-9999")) {
          this._notifyConnection(false);
        } else {
          this._notifyConnection(true);
        }

        resolve(response);
      };

      try {
        // Direct native messaging call is supported in extension pages with nativeMessaging permission
        if (typeof chrome.runtime.sendNativeMessage === "function") {
          chrome.runtime.sendNativeMessage("com.extbackup.pro", { action, payload }, handleResponse);
        } else {
          chrome.runtime.sendMessage({ action, payload }, handleResponse);
        }
      } catch (err) {
        clearTimeout(timer);
        this._notifyConnection(false);
        reject(err);
      }
    });
  }

  // System & Connection
  async ping() {
    return this.send("ping");
  }

  async getSystemInfo() {
    return this.send("get_system_info");
  }

  async getProfiles() {
    return this.send("get_profiles");
  }

  async getExtensions(profileId = "Default") {
    return this.send("get_extensions", { profile_id: profileId });
  }

  // Chrome Process Controls
  async checkChromeRunning() {
    return this.send("check_chrome_running");
  }

  async closeChrome() {
    return this.send("close_chrome");
  }

  // Backup Engine
  async backupExtension(options) {
    return this.send("backup_extension", options, 180000); // 3 min timeout for very large backups
  }

  async listBackups() {
    return this.send("list_backups");
  }

  async validateBackup(backupPath, password = null) {
    return this.send("validate_backup", { backup_path: backupPath, password });
  }

  // Restore Engine
  async restoreExtension(options) {
    return this.send("restore_extension", options, 180000);
  }

  async revertRollback(rollbackId, destinationPath) {
    return this.send("revert_rollback", { rollback_id: rollbackId, destination_path: destinationPath });
  }

  // Comparison & Diff
  async compareBackups(itemAPath, itemBPath, passwordA = null, passwordB = null) {
    return this.send("compare_backups", {
      item_a_path: itemAPath,
      item_b_path: itemBPath,
      password_a: passwordA,
      password_b: passwordB
    });
  }

  // Storage & Deletion
  async deleteBackup(backupPath) {
    return this.send("delete_backup", { backup_path: backupPath });
  }

  async scanCustomFolder(folderPath) {
    return this.send("scan_custom_folder", { folder_path: folderPath });
  }

  async checkDiskSpace(path = null) {
    return this.send("check_disk_space", { path });
  }

  // History & Logs
  async getHistory() {
    return this.send("get_history");
  }

  async getLogs() {
    return this.send("get_logs");
  }

  async exportLogs(targetFile = null) {
    return this.send("export_logs", { target_file: targetFile });
  }

  // Settings
  async getSettings() {
    return this.send("get_settings");
  }

  async saveSettings(settings) {
    return this.send("save_settings", { settings });
  }

  // Licensing
  async getLicense() {
    return this.send("get_license");
  }

  async activateLicense(licenseKey, registeredTo = "Utilizador Registado") {
    return this.send("activate_license", { license_key: licenseKey, registered_to: registeredTo });
  }

  async deactivateLicense() {
    return this.send("deactivate_license");
  }

  // Scheduler
  async getSchedule() {
    return this.send("get_schedule");
  }

  async saveSchedule(schedule) {
    return this.send("save_schedule", { schedule });
  }

  // Changes Monitoring
  async checkForChanges() {
    return this.send("check_for_changes");
  }

  // System actions
  async openFolder(folderPath) {
    return this.send("open_folder", { folder_path: folderPath });
  }

  async openChromeExtensions() {
    try {
      if (typeof chrome !== "undefined" && chrome.tabs && typeof chrome.tabs.create === "function") {
        chrome.tabs.create({ url: "chrome://extensions" });
      }
    } catch (e) {
      // ignore
    }
    return this.send("open_chrome_extensions");
  }

  async openFileDialog() {
    return this.send("open_file_dialog");
  }

  async inspectBackupFile(backupPath, password = null) {
    return this.send("inspect_backup_file", { backup_path: backupPath, password: password });
  }

  async importBackupFile(filename, base64Data) {
    return this.send("import_backup_file", { filename: filename, base64_data: base64Data });
  }

  async launchChromeWithExtension(folderPath) {
    return this.send("launch_chrome_with_extension", { folder_path: folderPath });
  }
}

// Global singleton
window.bridge = new NativeBridge();
