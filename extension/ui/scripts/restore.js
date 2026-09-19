/**
 * Chrome Extension Backup Pro - Restore & Rollback Controller
 * Step-by-step restore wizard, Chrome execution check, and rollback management.
 */

class RestoreController {
  constructor() {
    this.selectedBackupPath = "";
    this.lastRestoredPath = "";
    this.validationResult = null;
  }

  init() {
    if (this._initialized) return;
    this._initialized = true;

    const execBtn = document.getElementById("btn-execute-restore");
    if (execBtn) execBtn.addEventListener("click", () => this.executeRestore());

    const closeChromeBtn = document.getElementById("btn-close-chrome-controlled");
    if (closeChromeBtn) closeChromeBtn.addEventListener("click", () => this.requestControlledChromeClose());

    const openFolderBtn = document.getElementById("btn-restore-open-folder");
    if (openFolderBtn) openFolderBtn.addEventListener("click", () => this.openRestoredFolder());

    const copyPathBtn = document.getElementById("btn-restore-copy-path");
    if (copyPathBtn) copyPathBtn.addEventListener("click", () => this.copyRestoredPath());

    const openChromeBtn = document.getElementById("btn-restore-open-chrome");
    if (openChromeBtn) openChromeBtn.addEventListener("click", () => this.openChromeExtensionsPage());
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
        bannerText.textContent = `O Google Chrome está ativo (${res.count} processos). O restauro direto é seguro e protegido por salvaguarda prévia automática (Ponto de Rollback).`;
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

  async executeRestore(forceRun = true) {
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
      ? `diretamente no local ativo da extensão com salvaguarda prévia automática (Rollback Point)`
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
      password: password,
      force_even_if_chrome_running: forceRun
    });

    if (res.success) {
      this.lastRestoredPath = res.destination_path;
      const reportBox = document.getElementById("restore-report-container");
      reportBox.style.display = "block";
      document.getElementById("restore-report-ext").textContent = `${res.extension_name} (v${res.version})`;
      document.getElementById("restore-report-path").textContent = res.destination_path;
      document.getElementById("restore-report-files").textContent = `${res.copied_files} ficheiros restaurados`;
      document.getElementById("restore-report-rollback").textContent = res.rollback_id || "Nenhum (instalação nova)";
      document.getElementById("restore-report-notice").textContent = res.technical_notice || "";

      // Smoothly scroll down to the report box so buttons are immediately visible
      reportBox.scrollIntoView({ behavior: "smooth", block: "nearest" });

      window.app.showToast("Restauro concluído com 100% de integridade!", "success");
    } else {
      window.app.showErrorModal(res.error);
    }
  }

  async openRestoredFolder() {
    if (!this.lastRestoredPath) {
      window.app.showToast("Nenhuma pasta de restauro disponível.", "warning");
      return;
    }
    window.app.showToast("A abrir pasta no Explorador do Windows...", "info");
    const res = await window.bridge.openFolder(this.lastRestoredPath);
    if (res && res.error) {
      window.app.showToast(`Erro ao abrir pasta: ${res.error}`, "error");
    }
  }

  async copyRestoredPath() {
    if (!this.lastRestoredPath) {
      window.app.showToast("Nenhum caminho de restauro disponível.", "warning");
      return;
    }
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(this.lastRestoredPath);
      } else {
        const ta = document.createElement("textarea");
        ta.value = this.lastRestoredPath;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      }
      window.app.showToast("Caminho copiado para a Área de Transferência!", "success");
    } catch (e) {
      console.error("Erro ao copiar caminho:", e);
      window.app.showToast("Erro ao copiar caminho.", "error");
    }
  }

  async openChromeExtensionsPage() {
    window.app.showToast("A abrir página chrome://extensions...", "info");
    await window.bridge.openChromeExtensions();
  }
}

window.restoreController = new RestoreController();
