/**
 * Chrome Extension Backup Pro - Backups Catalog Controller
 * Manages .crxbackup archives, cryptographic integrity verification, locking, and deletion.
 * Complies 100% with Manifest V3 CSP (zero inline event handlers).
 */

class BackupsController {
  constructor() {
    this.backups = [];
    this.filteredBackups = [];
    this.searchQuery = "";
    this._initialized = false;
  }

  init() {
    if (this._initialized) return;
    this._initialized = true;

    // Search input
    const searchInput = document.getElementById("backups-search-input");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        this.setSearch(e.target.value);
      });
    }

    // Refresh button
    const refreshBtn = document.getElementById("btn-refresh-backups");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => {
        this.loadBackups();
      });
    }

    // Find backups button
    const findBtn = document.getElementById("btn-find-custom-backups");
    if (findBtn) {
      findBtn.addEventListener("click", () => {
        this.scanCustomFolderPrompt();
      });
    }

    // Import and restore external backup button
    const importRestoreBtn = document.getElementById("btn-import-restore-backup");
    if (importRestoreBtn) {
      importRestoreBtn.addEventListener("click", async () => {
        window.app.showToast("A abrir seletor de ficheiros (.crxbackup ou .zip)...", "info");
        try {
          const res = await window.bridge.openFileDialog();
          if (res && res.success && res.file_path) {
            window.app.navigate("restore");
            await window.restoreController.selectBackupForRestore(res.file_path);
          }
        } catch (e) {
          console.error("Erro ao abrir seletor de ficheiro:", e);
        }
      });
    }

    // Table body event delegation
    const tbody = document.getElementById("backups-tbody");
    if (tbody) {
      tbody.addEventListener("click", (e) => {
        const target = e.target.closest("button");
        if (!target) return;

        const action = target.dataset.action;
        const encodedPath = target.dataset.path;
        const isLocked = target.dataset.locked === "true";
        if (!encodedPath) return;

        if (action === "validate") {
          this.validateBackupFile(encodedPath);
        } else if (action === "restore") {
          this.restoreBackupFile(encodedPath);
        } else if (action === "compare") {
          this.compareBackupFile(encodedPath);
        } else if (action === "delete") {
          this.deleteBackupFile(encodedPath, isLocked);
        }
      });
    }
  }

  async loadBackups() {
    this.init();
    try {
      const tbody = document.getElementById("backups-tbody");
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 24px; color: var(--text-muted);"><span style="font-size: 18px;">⏳</span> A carregar catálogo de backups locais...</td></tr>`;
      }

      const res = await window.bridge.listBackups();
      this.backups = res.backups || [];
      this.applyFilters();
    } catch (err) {
      console.error("[Backups] Erro ao listar backups:", err);
      window.app.showToast("Falha ao ler diretório de backups.", "error");
    }
  }

  setSearch(query) {
    this.searchQuery = (query || "").toLowerCase().trim();
    this.applyFilters();
  }

  applyFilters() {
    let list = [...this.backups];
    if (this.searchQuery) {
      list = list.filter(
        (b) =>
          b.extension_name.toLowerCase().includes(this.searchQuery) ||
          b.extension_id.toLowerCase().includes(this.searchQuery) ||
          b.version.toLowerCase().includes(this.searchQuery) ||
          b.filename.toLowerCase().includes(this.searchQuery)
      );
    }
    this.filteredBackups = list;
    this.renderTable();
  }

  renderTable() {
    const tbody = document.getElementById("backups-tbody");
    if (!tbody) return;

    if (this.filteredBackups.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 32px; color: var(--text-muted);">Nenhum ficheiro de backup (.crxbackup ou .zip) encontrado na pasta de destino.</td></tr>`;
      return;
    }

    tbody.innerHTML = this.filteredBackups
      .map((b) => {
        const isZip = (b.filename && b.filename.endsWith(".zip")) || b.format === "zip";
        const fmtBadge = isZip
          ? `<span class="badge badge-info" style="font-size: 10px; margin-left: 6px;">ZIP</span>`
          : `<span class="badge badge-primary" style="font-size: 10px; margin-left: 6px;">CRXBACKUP</span>`;

        const lockIcon = b.is_locked ? "🔒" : "🔓";
        const lockText = b.is_locked ? "Bloqueado" : "Desbloqueado";
        const encBadge = b.is_encrypted
          ? `<span class="badge badge-warning" title="Protegido por AES-256">AES Encriptado</span>`
          : `<span class="badge badge-gray">Normal</span>`;

        const encPath = encodeURIComponent(b.path);

        return `
        <tr>
          <td>
            <div style="display: flex; align-items: center;">
              <span style="font-weight: 600; color: var(--text-primary);">${b.extension_name}</span>
              ${fmtBadge}
            </div>
            <div style="font-family: monospace; font-size: 11px; color: var(--text-muted);">${b.filename}</div>
          </td>
          <td><span class="badge badge-gray">v${b.version}</span></td>
          <td>${b.chrome_profile || "Default"}</td>
          <td>${b.size_formatted}</td>
          <td style="font-size: 12px; color: var(--text-secondary);">${b.backup_date}</td>
          <td>${encBadge}</td>
          <td>
            <span class="badge ${b.is_locked ? "badge-info" : "badge-gray"}">${lockIcon} ${lockText}</span>
          </td>
          <td>
            <div style="display: flex; gap: 4px;">
              <button class="btn btn-primary btn-sm" data-action="validate" data-path="${encPath}" title="Validar Hashes SHA-256">Validar</button>
              <button class="btn btn-secondary btn-sm" data-action="restore" data-path="${encPath}" title="Restaurar este backup">Restaurar</button>
              <button class="btn btn-secondary btn-sm" data-action="compare" data-path="${encPath}" title="Comparar com outra versão">Comparar</button>
              <button class="btn btn-danger btn-sm" data-action="delete" data-path="${encPath}" data-locked="${b.is_locked}" title="Eliminar arquivo">🗑️</button>
            </div>
          </td>
        </tr>
      `;
      })
      .join("");
  }

  async validateBackupFile(encodedPath) {
    const backupPath = decodeURIComponent(encodedPath);
    window.app.showToast("A validar integridade SHA-256 dos ficheiros...", "info");

    try {
      const res = await window.bridge.validateBackup(backupPath);
      if (res.valid) {
        window.app.showToast(`Backup 100% íntegro! (${res.identical_count} ficheiros validados)`, "success");
      } else {
        const errDetails = res.error || "Discrepância detetada nos hashes.";
        window.app.showErrorModal({
          code: "VL-0002",
          title: "Backup Inválido ou Corrompido",
          description: errDetails,
          operation: "validate_backup",
          solution: "O arquivo pode ter sido modificado ou truncado. Não utilize este backup para restauro."
        });
      }
    } catch (e) {
      window.app.showToast(`Erro na validação: ${e.message}`, "error");
    }
  }

  restoreBackupFile(encodedPath) {
    const backupPath = decodeURIComponent(encodedPath);
    window.restoreController.selectBackupForRestore(backupPath);
    window.app.navigate("restore");
  }

  compareBackupFile(encodedPath) {
    const backupPath = decodeURIComponent(encodedPath);
    window.compareController.setItemA(backupPath);
    window.app.navigate("compare");
  }

  async deleteBackupFile(encodedPath, isLocked) {
    const backupPath = decodeURIComponent(encodedPath);
    if (isLocked) {
      window.app.showToast("Este backup está bloqueado contra eliminação.", "warning");
      return;
    }

    if (!confirm(`Tem a certeza que deseja eliminar permanentemente este backup?\n\n${backupPath}`)) {
      return;
    }

    try {
      const res = await window.bridge.deleteBackup(backupPath);
      if (res.success) {
        window.app.showToast("Backup eliminado com sucesso.", "success");
        this.loadBackups();
      } else {
        window.app.showToast(`Falha ao eliminar: ${res.message}`, "error");
      }
    } catch (e) {
      window.app.showToast(`Erro ao eliminar: ${e.message}`, "error");
    }
  }

  async scanCustomFolderPrompt() {
    const folder = prompt("Insira o caminho da pasta a pesquisar por ficheiros .crxbackup (ex: D:\\Backups):");
    if (!folder) return;

    window.app.showToast(`A pesquisar backups em ${folder}...`, "info");
    try {
      const res = await window.bridge.scanCustomFolder(folder);
      if (res.success) {
        window.app.showToast(`Encontrados ${res.count} backups válidos na pasta.`, "success");
        this.backups = res.backups || [];
        this.applyFilters();
      } else {
        window.app.showToast(res.message || "Erro ao analisar pasta.", "error");
      }
    } catch (e) {
      window.app.showToast(`Erro ao ler pasta: ${e.message}`, "error");
    }
  }
}

window.backupsController = new BackupsController();
