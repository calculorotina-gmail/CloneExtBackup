/**
 * Chrome Extension Backup Pro - Restore & Rollback Controller
 * Step-by-step restore wizard, Chrome execution check, and rollback management.
 */

class RestoreController {
  constructor() {
    this.selectedBackupPath = "";
    this.lastRestoredPath = "";
    this.sourceMode = "catalog"; // "catalog" or "custom_file"
    this.customFileInfo = null;
    this.validationResult = null;
    this._initialized = false;
  }

  init() {
    if (this._initialized) return;
    this._initialized = true;

    // Execution & control buttons
    const execBtn = document.getElementById("btn-execute-restore");
    if (execBtn) execBtn.addEventListener("click", () => this.executeRestore());

    const closeChromeBtn = document.getElementById("btn-close-chrome-controlled");
    if (closeChromeBtn) closeChromeBtn.addEventListener("click", () => this.requestControlledChromeClose());

    // Post-restore buttons
    const launchChromeBtn = document.getElementById("btn-restore-launch-chrome");
    if (launchChromeBtn) launchChromeBtn.addEventListener("click", () => this.launchChromeWithCurrentExtension());

    const openFolderBtn = document.getElementById("btn-restore-open-folder");
    if (openFolderBtn) openFolderBtn.addEventListener("click", () => this.openRestoredFolder());

    const copyPathBtn = document.getElementById("btn-restore-copy-path");
    if (copyPathBtn) copyPathBtn.addEventListener("click", () => this.copyRestoredPath());

    const openChromeBtn = document.getElementById("btn-restore-open-chrome");
    if (openChromeBtn) openChromeBtn.addEventListener("click", () => this.openChromeExtensionsPage());

    // Source switching tabs
    const btnSourceCatalog = document.getElementById("btn-source-catalog");
    if (btnSourceCatalog) {
      btnSourceCatalog.addEventListener("click", () => this.setSourceMode("catalog"));
    }

    const btnSourceCustom = document.getElementById("btn-source-custom-file");
    if (btnSourceCustom) {
      btnSourceCustom.addEventListener("click", () => this.setSourceMode("custom_file"));
    }

    // Native file dialog button
    const browseNativeBtn = document.getElementById("btn-browse-crxbackup-native");
    if (browseNativeBtn) {
      browseNativeBtn.addEventListener("click", () => this.browseNativeFile());
    }

    // HTML file input
    const fileInput = document.getElementById("crxbackup-file-input");
    if (fileInput) {
      fileInput.addEventListener("change", (e) => this.handleFileInput(e));
    }

    // Dropzone
    const dropzone = document.getElementById("crxbackup-dropzone");
    if (dropzone) {
      dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
      });
      dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("dragover");
      });
      dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
          this.processDroppedFile(e.dataTransfer.files[0]);
        }
      });
    }

    // Change listener on catalog select
    const sel = document.getElementById("restore-backup-select");
    if (sel) {
      sel.addEventListener("change", (e) => {
        this.selectedBackupPath = e.target.value;
      });
    }
  }

  setSourceMode(mode) {
    this.sourceMode = mode;
    const btnCatalog = document.getElementById("btn-source-catalog");
    const btnCustom = document.getElementById("btn-source-custom-file");
    const containerCatalog = document.getElementById("source-catalog-container");
    const containerCustom = document.getElementById("source-custom-file-container");

    if (mode === "catalog") {
      if (btnCatalog) btnCatalog.classList.add("active");
      if (btnCustom) btnCustom.classList.remove("active");
      if (containerCatalog) containerCatalog.style.display = "block";
      if (containerCustom) containerCustom.style.display = "none";
      const sel = document.getElementById("restore-backup-select");
      if (sel) this.selectedBackupPath = sel.value;
    } else {
      if (btnCatalog) btnCatalog.classList.remove("active");
      if (btnCustom) btnCustom.classList.add("active");
      if (containerCatalog) containerCatalog.style.display = "none";
      if (containerCustom) containerCustom.style.display = "block";
      if (this.customFileInfo) {
        this.selectedBackupPath = this.customFileInfo.backup_path;
      }
    }
  }

  async browseNativeFile() {
    window.app.showToast("A abrir seletor de ficheiros do Windows...", "info");
    try {
      const res = await window.bridge.openFileDialog();
      if (res && res.success && res.file_path) {
        await this.inspectAndSelectBackup(res.file_path);
      } else if (res && res.cancelled) {
        // cancelled
      } else if (res && res.error) {
        window.app.showToast(`Erro ao abrir seletor: ${res.error}`, "error");
      }
    } catch (e) {
      console.error("Erro no seletor nativo:", e);
      window.app.showToast("Falha ao abrir seletor de ficheiros.", "error");
    }
  }

  async handleFileInput(e) {
    const file = e.target.files && e.target.files[0];
    if (file) {
      await this.processDroppedFile(file);
    }
  }

  async processDroppedFile(file) {
    if (!file.name.endsWith(".crxbackup") && !file.name.endsWith(".zip")) {
      window.app.showToast("Selecione um ficheiro com a extensão .crxbackup.", "warning");
      return;
    }

    window.app.showToast(`A importar ficheiro ${file.name}...`, "info");
    try {
      const reader = new FileReader();
      reader.onload = async () => {
        const base64 = reader.result.split(",")[1];
        const res = await window.bridge.importBackupFile(file.name, base64);
        if (res && res.success && res.file_path) {
          this.applyInspectedBackupInfo(res.info, res.file_path);
          window.app.showToast("Ficheiro .crxbackup validado com sucesso!", "success");
        } else {
          window.app.showToast(res.error || "Erro ao importar ficheiro.", "error");
        }
      };
      reader.readAsDataURL(file);
    } catch (err) {
      window.app.showToast(`Erro ao processar ficheiro: ${err.message}`, "error");
    }
  }

  async inspectAndSelectBackup(filePath) {
    window.app.showToast("A verificar integridade e metadados do backup...", "info");
    try {
      const res = await window.bridge.inspectBackupFile(filePath);
      if (res && res.success && res.info) {
        this.applyInspectedBackupInfo(res.info, filePath);
        window.app.showToast(`Backup ${res.info.extension_name} (v${res.info.version}) verificado!`, "success");
      } else {
        window.app.showErrorModal({
          code: "VL-0002",
          title: "Arquivo .crxbackup Inválido",
          description: res.error || "Não foi possível validar a integridade deste arquivo de backup.",
          operation: "inspect_backup_file",
          solution: "Verifique se o ficheiro não está corrompido ou protegido por senha."
        });
      }
    } catch (e) {
      window.app.showToast(`Erro ao inspecionar: ${e.message}`, "error");
    }
  }

  applyInspectedBackupInfo(info, filePath) {
    this.customFileInfo = info;
    this.selectedBackupPath = filePath;
    this.setSourceMode("custom_file");

    const card = document.getElementById("selected-crxbackup-card");
    if (card) {
      card.style.display = "block";
      document.getElementById("custom-file-ext-name").textContent = info.extension_name;
      document.getElementById("custom-file-ext-ver").textContent = `v${info.version}`;
      document.getElementById("custom-file-size").textContent = info.size_formatted;
      document.getElementById("custom-file-files").textContent = `${info.file_count} ficheiros`;
      document.getElementById("custom-file-path-display").textContent = filePath;
    }
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

      if (this.selectedBackupPath && this.sourceMode === "catalog") {
        sel.value = this.selectedBackupPath;
      } else if (!this.selectedBackupPath) {
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

  async selectBackupForRestore(path) {
    this.selectedBackupPath = path;
    const sel = document.getElementById("restore-backup-select");
    let foundInCatalog = false;
    if (sel && sel.options) {
      for (let i = 0; i < sel.options.length; i++) {
        if (sel.options[i].value === path) {
          sel.selectedIndex = i;
          foundInCatalog = true;
          break;
        }
      }
    }

    if (foundInCatalog) {
      this.setSourceMode("catalog");
    } else {
      await this.inspectAndSelectBackup(path);
    }
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
    const profileSelect = document.getElementById("restore-profile-select");
    const modeSelect = document.getElementById("restore-mode-select");
    const passwordInput = document.getElementById("restore-password-input");

    let backupPath = this.selectedBackupPath;
    if (this.sourceMode === "catalog") {
      const backupSelect = document.getElementById("restore-backup-select");
      if (backupSelect) backupPath = backupSelect.value;
    }

    const targetProfile = profileSelect ? profileSelect.value : "Default";
    const restoreMode = modeSelect ? modeSelect.value : "auto_chrome";
    const password = passwordInput ? passwordInput.value.trim() : null;

    if (!backupPath) {
      window.app.showToast("Selecione um ficheiro de backup (.crxbackup) para restaurar.", "warning");
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

    let modeDesc = "Restauro Completo no Chrome (Registar nas Extensões + Extrair Ficheiros)";
    if (restoreMode === "unpacked_export") {
      modeDesc = "Exportação Descompactada (Modo de Programador / Load Unpacked)";
    } else if (restoreMode === "direct_profile") {
      modeDesc = "Restauro Físico no Perfil";
    }

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

      const regBadge = document.getElementById("restore-report-chrome-reg-badge");
      if (regBadge) {
        regBadge.style.display = res.chrome_registered ? "block" : "none";
      }

      // Smoothly scroll down to the report box so buttons are immediately visible
      reportBox.scrollIntoView({ behavior: "smooth", block: "nearest" });

      window.app.showToast("Restauro concluído com 100% de integridade!", "success");
    } else {
      window.app.showErrorModal(res.error);
    }
  }

  async launchChromeWithCurrentExtension() {
    if (!this.lastRestoredPath) {
      window.app.showToast("Nenhuma pasta de restauro disponível.", "warning");
      return;
    }
    window.app.showToast("A abrir Google Chrome com a extensão carregada...", "info");
    const res = await window.bridge.launchChromeWithExtension(this.lastRestoredPath);
    if (res && res.error) {
      window.app.showToast(`Erro ao iniciar Chrome: ${res.error}`, "error");
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
