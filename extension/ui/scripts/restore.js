/**
 * Chrome Extension Backup Pro - Restore & Rollback Controller
 * Step-by-step restore wizard, Chrome execution check, and rollback management.
 */

class RestoreController {
  constructor() {
    this.selectedBackupPath = "";
    this.validationResult = null;
  }

  init() {
    if (this._initialized) return;
    this._initialized = true;

    const execBtn = document.getElementById("btn-execute-restore");
    if (execBtn) execBtn.addEventListener("click", () => this.executeRestore());

    const closeChromeBtn = document.getElementById("btn-close-chrome-controlled");
    if (closeChromeBtn) closeChromeBtn.addEventListener("click", () => this.requestControlledChromeClose());
  }

  async initRestoreView() {
    this.init();
    await this.populateBackupDropdown();
    await this.populateProfileDropdown();
    this.checkChromeStatus();
  }

  async populateBackupDropdown() {
    const sel = document.getElementById("restore-backup-select");
    if (!sel) return;

    try {
      const res = await window.bridge.listBackups();
      const backups = res.backups || [];
      if (backups.length === 0) {
        sel.innerHTML = `<option value="">Nenhum backup encontrado na pasta padrão</option>`;
        return;
      }

      sel.innerHTML = backups
        .map((b) => `<option value="${b.path}">${b.extension_name} (v${b.version}) - ${b.backup_date} [${b.size_formatted}]</option>`)
        .join("");

      if (this.selectedBackupPath) {
        sel.value = this.selectedBackupPath;
      } else {
        this.selectedBackupPath = sel.value;
      }
    } catch (e) {
      console.error("Erro ao popular backups para restauro:", e);
    }
  }

  async populateProfileDropdown() {
    const sel = document.getElementById("restore-profile-select");
    if (!sel) return;

    try {
      const res = await window.bridge.getProfiles();
      const profiles = res.profiles || [];
      sel.innerHTML = profiles
        .map((p) => `<option value="${p.profile_id}">${p.name} (${p.profile_id})</option>`)
        .join("");

      if (window.app.currentProfileId) {
        sel.value = window.app.currentProfileId;
      }
    } catch (e) {
      console.error("Erro ao popular perfis:", e);
    }
  }

  selectBackupForRestore(path) {
    this.selectedBackupPath = path;
    const sel = document.getElementById("restore-backup-select");
    if (sel) sel.value = path;
  }

  async checkChromeStatus() {
    const banner = document.getElementById("restore-chrome-warning");
    const bannerText = document.getElementById("restore-chrome-text");
    const closeBtn = document.getElementById("btn-close-chrome-controlled");

    try {
      const res = await window.bridge.checkChromeRunning();
      if (res.running) {
        banner.style.display = "block";
        bannerText.textContent = `Atenção: O Google Chrome está aberto com ${res.count} processos ativos. Para o restauro direto no perfil, é recomendável fechar o Chrome para evitar locks de ficheiros.`;
        closeBtn.style.display = "inline-flex";
      } else {
        banner.style.display = "none";
      }
    } catch (e) {
      console.warn("Erro ao verificar Chrome:", e);
    }
  }

  async requestControlledChromeClose() {
    if (!confirm("Deseja fechar o Google Chrome de forma controlada agora para permitir o restauro sem locks de ficheiro?")) {
      return;
    }

    window.app.showToast("A solicitar fecho controlado do Chrome...", "info");
    try {
      const res = await window.bridge.closeChrome();
      if (res.closed) {
        window.app.showToast("Google Chrome fechado com sucesso.", "success");
        this.checkChromeStatus();
      } else {
        window.app.showToast(res.message || "Não foi possível fechar o Chrome.", "warning");
      }
    } catch (e) {
      window.app.showToast(`Erro: ${e.message}`, "error");
    }
  }

  async executeRestore() {
    const backupSelect = document.getElementById("restore-backup-select");
    const profileSelect = document.getElementById("restore-profile-select");
    const modeSelect = document.getElementById("restore-mode-select");
    const passwordInput = document.getElementById("restore-password-input");

    const backupPath = backupSelect.value;
    const targetProfile = profileSelect.value;
    const restoreMode = modeSelect.value; // "direct_profile" or "unpacked_export"
    const password = passwordInput ? passwordInput.value.trim() : null;

    if (!backupPath) {
      window.app.showToast("Selecione um ficheiro de backup para restaurar.", "warning");
      return;
    }

    // Step 1: Pre-validation of integrity
    window.app.showToast("A validar integridade do backup antes do restauro...", "info");
    const val = await window.bridge.validateBackup(backupPath, password);
    if (!val.valid) {
      window.app.showErrorModal({
        code: "RS-0001",
        title: "Validação Prévia Falhou",
        description: val.error || "O arquivo de backup falhou na verificação de integridade dos ficheiros SHA-256.",
        operation: "restore_pre_validation",
        solution: "O restauro foi cancelado para proteger o perfil do Chrome. Utilize outro backup válido."
      });
      return;
    }

    // Step 2: Confirm restore
    const modeDesc = restoreMode === "direct_profile" 
      ? `diretamente no perfil '${targetProfile}' com salvaguarda prévia automática (Rollback Point)`
      : `exportando para pasta local pronta para carregar no Modo de Programador (chrome://extensions)`;

    if (!confirm(`Confirma a operação de restauro?\n\nModo: ${modeDesc}\n\nFicheiro: ${backupPath}`)) {
      return;
    }

    // Step 3: Run restore
    window.app.showToast("A executar restauro dos ficheiros locais...", "info");
    const res = await window.bridge.restoreExtension({
      backup_path: backupPath,
      target_profile: targetProfile,
      restore_mode: restoreMode,
      password: password
    });

    if (res.success) {
      const reportBox = document.getElementById("restore-report-container");
      reportBox.style.display = "block";
      document.getElementById("restore-report-ext").textContent = `${res.extension_name} (v${res.version})`;
      document.getElementById("restore-report-path").textContent = res.destination_path;
      document.getElementById("restore-report-files").textContent = `${res.copied_files} ficheiros restaurados`;
      document.getElementById("restore-report-rollback").textContent = res.rollback_id || "Nenhum (instalação nova)";
      document.getElementById("restore-report-notice").textContent = res.technical_notice || "";

      window.app.showToast("Restauro concluído com 100% de integridade!", "success");
    } else {
      window.app.showErrorModal(res.error);
    }
  }
}

window.restoreController = new RestoreController();
