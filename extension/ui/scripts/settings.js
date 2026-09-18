/**
 * Chrome Extension Backup Pro - Settings Controller
 * Manages user preferences, compression, paths, security, and notification triggers.
 */

class SettingsController {
  constructor() {
    this.settings = {};
  }

  init() {
    if (this._initialized) return;
    this._initialized = true;

    const saveBtn = document.getElementById("btn-save-settings");
    if (saveBtn) saveBtn.addEventListener("click", () => this.saveSettings());
  }

  async loadSettings() {
    this.init();
    try {
      const res = await window.bridge.getSettings();
      this.settings = res.settings || {};
      this.populateForm();
    } catch (e) {
      console.error("Erro ao carregar definições:", e);
    }
  }

  populateForm() {
    const s = this.settings;
    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val !== undefined ? val : "";
    };
    const setChecked = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.checked = !!val;
    };

    setVal("setting-primary-dir", s.primary_backup_dir);
    setVal("setting-secondary-dir", s.secondary_backup_dir);
    setChecked("setting-auto-secondary", s.auto_secondary_backup);
    setVal("setting-compression", s.compression_level);
    setChecked("setting-incremental", s.is_incremental);
    setChecked("setting-encryption", s.encryption_enabled);
    setVal("setting-password", s.encryption_password);
    setVal("setting-theme", s.theme || "system");
    setVal("setting-retention-versions", s.retention_max_versions || 5);
    setVal("setting-retention-days", s.retention_days || 30);
    setVal("setting-custom-chrome-dir", s.custom_chrome_user_data);

    setChecked("setting-notify-success", s.notify_on_success !== false);
    setChecked("setting-notify-error", s.notify_on_error !== false);
    setChecked("setting-notify-change", s.notify_on_change !== false);
    setChecked("setting-confirm-restore", s.confirm_before_restore !== false);
    setChecked("setting-auto-rollback", s.create_rollback_before_restore !== false);
  }

  async saveSettings() {
    const getVal = (id) => document.getElementById(id)?.value || "";
    const getChecked = (id) => !!document.getElementById(id)?.checked;

    const newSettings = {
      primary_backup_dir: getVal("setting-primary-dir").trim(),
      secondary_backup_dir: getVal("setting-secondary-dir").trim(),
      auto_secondary_backup: getChecked("setting-auto-secondary"),
      compression_level: parseInt(getVal("setting-compression") || "6", 10),
      is_incremental: getChecked("setting-incremental"),
      encryption_enabled: getChecked("setting-encryption"),
      encryption_password: getVal("setting-password").trim(),
      theme: getVal("setting-theme"),
      retention_max_versions: parseInt(getVal("setting-retention-versions") || "5", 10),
      retention_days: parseInt(getVal("setting-retention-days") || "30", 10),
      custom_chrome_user_data: getVal("setting-custom-chrome-dir").trim(),
      notify_on_success: getChecked("setting-notify-success"),
      notify_on_error: getChecked("setting-notify-error"),
      notify_on_change: getChecked("setting-notify-change"),
      confirm_before_restore: getChecked("setting-confirm-restore"),
      create_rollback_before_restore: getChecked("setting-auto-rollback")
    };

    window.app.showToast("A guardar definições...", "info");
    try {
      const res = await window.bridge.saveSettings(newSettings);
      if (res.success) {
        window.app.showToast("Definições guardadas com sucesso!", "success");
        this.settings = res.settings;
        // Apply theme immediately
        window.app.setTheme(newSettings.theme);
      } else {
        window.app.showToast("Erro ao gravar definições.", "error");
      }
    } catch (e) {
      window.app.showToast(`Erro: ${e.message}`, "error");
    }
  }
}

window.settingsController = new SettingsController();
